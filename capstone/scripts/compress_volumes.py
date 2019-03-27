import csv
import gzip
import json
import logging
import tarfile
import tempfile
import os
from contextlib import contextmanager
from io import BytesIO
from collections import defaultdict
from datetime import datetime
from multiprocessing.pool import ThreadPool
from celery import shared_task
import time
from pathlib import Path
from tempfile import TemporaryDirectory
import shutil
import subprocess
import copy

from django.conf import settings
from django.template.defaultfilters import filesizeformat

from capdb.storages import captar_storage, get_storage, CaptarStorage, CapS3Storage, CapFileStorage
from scripts.helpers import copy_file, parse_xml, resolve_namespace, serialize_xml, HashingFile, \
    volume_barcode_from_folder, storage_lookup

# logging
# disable boto3 info logging -- see https://github.com/boto/boto3/issues/521

logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('nose').setLevel(logging.WARNING)
logging.getLogger('s3transfer').setLevel(logging.WARNING)
logger = logging.getLogger(__name__)
info = logger.info
info = print


# separate function to check .tar integrity against volmets
# encryption?

### HELPERS ###

def get_file_type(path):
    """ Sort volume files by type. """
    if 'alto/' in path:
        if path.endswith('.xml') or path.endswith('.xml.gz'):
            return 'alto'
        return None
    if 'images/' in path:
        if path.endswith('.jp2'):
            return 'jp2'
        if path.endswith('.jpg'):
            return 'jp2'
        if path.endswith('.tif'):
            return 'tif'
        if path.endswith('.pdf'):
            return 'pdf'
        return None
    if 'casemets/' in path:
        if path.endswith('.xml') or path.endswith('.xml.gz'):
            return 'case'
        return None
    if path.endswith('METS.md5'):
        return 'md5'
    if path.endswith('METS.xml') or path.endswith('METS.xml.gz'):
        return 'volume'
    if path.endswith('BOXES.xml') or path.endswith('BOXES.xml.gz'):
        return 'boxes'
    return None

def files_by_type(files):
    """ Sort list of paths into dict by type. """
    out = defaultdict(list)
    for f in files:
        out[get_file_type(f)].append(f)
    return out

class LoggingTarFile(tarfile.TarFile):
    def addfile(self, tarinfo, fileobj=None):
        """
            Source copied from tarfile.TarFile, except for setting tarinfo.offset and tarinfo.offset_data.
        """
        self._check("awx")

        tarinfo = copy.copy(tarinfo)

        # NEW LINE
        tarinfo.offset = self.offset

        buf = tarinfo.tobuf(self.format, self.encoding, self.errors)
        self.fileobj.write(buf)
        self.offset += len(buf)

        # NEW LINE
        tarinfo.offset_data = self.offset

        # If there's data to follow, append it.
        if fileobj is not None:
            tarfile.copyfileobj(fileobj, self.fileobj, tarinfo.size)
            blocks, remainder = divmod(tarinfo.size, tarfile.BLOCKSIZE)
            if remainder > 0:
                self.fileobj.write(tarfile.NUL * (tarfile.BLOCKSIZE - remainder))
                blocks += 1
            self.offset += blocks * tarfile.BLOCKSIZE

        self.members.append(tarinfo)

def jp2_to_jpg(jp2_file, quality=50):
    """
        Convert jp2_file, an open file handle, to jpg and return jpg data.
        Requires opj_decompress and mozcjpeg to be in PATH.
    """
    with tempfile.NamedTemporaryFile(suffix=".jp2") as jp2_temp_file, \
         tempfile.TemporaryDirectory() as tga_dir:

        # create temp jp2 on disk, required by obj_decompress
        shutil.copyfileobj(jp2_file, jp2_temp_file)
        jp2_temp_file.flush()

        # create named pipe from opj_decompress to mozcjpeg
        tga_pipe = os.path.join(tga_dir, "pipe.tga")
        os.mkfifo(tga_pipe)

        try:
            # run opj_decompress to convert jp2 to tga, writing to named pipe
            proc = subprocess.Popen([
                "opj_decompress",
                "-i", jp2_temp_file.name,
                "-o", tga_pipe,
                "-threads", "5",  # on a quick test, 5 threads seems to be fastest
                "-quiet",  # suppress progress messages
            ])

            # run mozcjpeg to convert tga to jpg, reading from named pipe
            proc2 = subprocess.Popen([
                "mozcjpeg",
                "-quality", str(quality),
                "-targa", tga_pipe
            ], stdout=subprocess.PIPE)

            # fetch jpg from mozcjpeg
            out, err = proc2.communicate()

        finally:
            # make sure proc actually ended
            proc.kill()

        if err:
            raise Exception("Error calling cjpeg: %s" % err)

        return out

def jp2_to_jpg_slow(jp2_file, quality=40):
    """
        Convert jp2_file, an open file handle, to jpg and return jpg data.
        Requires opj_decompress and mozcjpeg to be in PATH.
    """
    with tempfile.NamedTemporaryFile(suffix=".jp2") as jp2_temp_file, \
         tempfile.TemporaryDirectory() as tga_dir:

        # create temp jp2 on disk, required by obj_decompress
        shutil.copyfileobj(jp2_file, jp2_temp_file)
        jp2_temp_file.flush()

        tga_file = os.path.join(tga_dir, "temp.tga")

        subprocess.check_call([
            "opj_decompress",
            "-i", jp2_temp_file.name,
            "-o", tga_file,
            "-threads", "5",  # on a quick test, 5 threads seems to be fastest
            "-quiet",  # suppress progress messages
        ])

        out = subprocess.check_output([
            "mozcjpeg",
            "-quality", str(quality),
            "-targa", tga_file
        ])

        return out

def compress_jp2(in_file, quality=35):
    """
        Convert in_file, an open file handle, to compressed jp2.
        Requires opj_compress to be in PATH.
    """
    with tempfile.NamedTemporaryFile(suffix=".jp2") as jp2_temp_file, \
         tempfile.NamedTemporaryFile(suffix=".tga") as tga_temp_file:

        # create temp jp2 on disk, required by obj_compress
        shutil.copyfileobj(in_file, jp2_temp_file)
        jp2_temp_file.flush()

        subprocess.check_call([
            "opj_decompress",
            "-i", jp2_temp_file.name,
            "-o", tga_temp_file.name,
            "-threads", "5",  # on a quick test, 5 threads seems to be fastest
            "-quiet",  # suppress progress messages
        ])

        subprocess.check_call([
            "opj_compress",
            "-i", tga_temp_file.name,
            "-o", jp2_temp_file.name,
            "-q", str(quality),
            "-quiet",  # suppress progress messages
        ])

        # return small jp2 data
        with open(jp2_temp_file.name, "rb") as out:
            return out.read()

def tif_to_png(tif_file):
    """
        Convert tif_file, an open file handle, to png and return png data.
        Requires ImageMagick convert and optipng to be in PATH.
    """

    with tempfile.NamedTemporaryFile(suffix=".tif") as tif_temp_file, \
         tempfile.NamedTemporaryFile(suffix=".png") as png_temp_file:

        # write tif file
        shutil.copyfileobj(tif_file, tif_temp_file)
        tif_temp_file.flush()

        # tif -> png
        subprocess.check_call([
            "convert", tif_temp_file.name, "-monochrome", png_temp_file.name
        ])

        # png -> small png
        subprocess.check_call([
            "optipng",
            "-strip", "all",  # strip metadata
            "-f0",  # use filter zero -- seems to be preferred for our images, and it's faster not to check all
            "-i0",  # not interlaced for smaller size
            "-force",  # export png data even if input is smaller
            png_temp_file.name
        ], stderr=subprocess.DEVNULL)

        # return small png data
        with open(png_temp_file.name, "rb") as out:
            return out.read()

def write_xml_gz(xml, out_path):
    """
        Write xml to out_path, with .xml.gz suffix, returning a tuple of:
            out_file: file wrapper with digest info
            out_path: out_path with new suffix
    """
    if type(xml) != bytes:
        xml = serialize_xml(xml)
    out_path = out_path.with_suffix('.xml.gz')
    with out_path.open('wb') as out_file:
        out_file = HashingFile(out_file)
        with gzip.GzipFile(fileobj=out_file) as gz_file:
            gz_file.write(xml)
    return out_file, out_path

### FILE HANDLERS ###

def handle_simple_file(volume_file_path, tempdir, storage_name):
    storage, out_path = single_file_setup(volume_file_path, tempdir, storage_name)
    copy_file(volume_file_path, str(out_path), from_storage=storage)

def handle_image_file(volume_file_path, tempdir, storage_name, new_suffix, conversion_function):
    storage, out_path = single_file_setup(volume_file_path, tempdir, storage_name)

    out_path = out_path.with_suffix(new_suffix)
    start_time = time.time()
    with storage.open(volume_file_path, "rb") as im_file:
        converted_image_data = conversion_function(im_file)

    with out_path.open("wb") as out_file:
        out_file = HashingFile(out_file)
        out_file.write(converted_image_data)
    info("Compress time:", time.time() - start_time)

    return format_new_file_info(volume_file_path, out_path, out_file)

def handle_alto_file(volume_file_path, tempdir, storage_name):
    storage, out_path = single_file_setup(volume_file_path, tempdir, storage_name)

    with storage.open(volume_file_path, "r") as in_file:
        alto_xml = parse_xml(in_file.read())

    filename_el = alto_xml('alto|fileName')
    filename_el.text(filename_el.text().replace('.tif', '.png'))

    pstep_el = alto_xml('alto|processingStepDescription')
    pstep_el.text(pstep_el.text().replace('TIFF', 'PNG'))

    # write out xml
    out_file, out_path = write_xml_gz(alto_xml, out_path)
    return format_new_file_info(volume_file_path, out_path, out_file)

def handle_mets_file(volume_file_path, tempdir, storage_name, new_file_info, relative_path_prefix=''):
    storage, out_path = single_file_setup(volume_file_path, tempdir, storage_name)

    with storage.open(volume_file_path, "r") as in_file:
        mets_xml = parse_xml(in_file.read())

    # add provenance data
    # spacing at start and end of string matters here -- makes sure formatting matches surrounding elements
    mets_xml('mets|amdSec').append("""  <digiprovMD ID="digi004">
      <mdWrap MDTYPE="PREMIS">
        <xmlData>
          <event xmlns="info:lc/xmlns/premis-v2">
            <eventIdentifier>
              <eventIdentifierType>Local</eventIdentifierType>
              <eventIdentifierValue>proc0001</eventIdentifierValue>
            </eventIdentifier>
            <eventType>compression</eventType>
            <eventDateTime>%s</eventDateTime>
            <eventDetail>File compression</eventDetail>
          </event>
          <agent xmlns="info:lc/xmlns/premis-v2">
            <agentIdentifier>
              <agentIdentifierType>Local</agentIdentifierType>
              <agentIdentifierValue>HLSL</agentIdentifierValue>
            </agentIdentifier>
            <agentName>Harvard Law School Library</agentName>
            <agentType>organization</agentType>
          </agent>
        </xmlData>
      </mdWrap>
    </digiprovMD>
  """ % (datetime.utcnow().isoformat().split('.')[0]+'Z'))

    # update <fileGrp> sections
    fptr_elements = mets_xml('mets|fptr')

    def fix_file_group(group_name, new_mime_type=None, new_id_prefix=None):
        file_group = mets_xml('mets|fileGrp[USE="%s"]' % group_name)
        for file_el in file_group('mets|file'):
            file_el = parse_xml(file_el)
            flocat_el = file_el('mets|FLocat')
            old_href = flocat_el.attr(resolve_namespace('xlink|href'))
            new_data = new_file_info[old_href.replace(relative_path_prefix, '')]

            if new_id_prefix:
                file_el.attr('ID', file_el.attr('ID').replace(group_name, new_id_prefix))
            if new_mime_type:
                file_el.attr('MIMETYPE', new_mime_type)
            file_el.attr('CHECKSUM', new_data['digest'])
            file_el.attr('SIZE', str(new_data['length']))

            flocat_el.attr(resolve_namespace('xlink|href'), relative_path_prefix+new_data['new_path'])

        if new_id_prefix:
            # fix fileGrp element
            file_group.attr('USE', new_id_prefix)

            # fix <fptr> elements
            for fptr in fptr_elements:
                fileid = fptr.attrib.get('FILEID', '')
                if fileid.startswith(group_name):
                    fptr.attrib['FILEID'] = fileid.replace(group_name, new_id_prefix)

    fix_file_group('jp2', 'image/jpg', 'jpg')
    # use this if doing jp2 -> compressed jp2
    # fix_file_group('jp2')
    # use this if compressing tiff -> png
    # fix_file_group('tiff', 'image/png', 'png')
    fix_file_group('alto', 'text/xml+gzip')
    fix_file_group('casemets', 'text/xml+gzip')

    # write out xml
    out_file, out_path = write_xml_gz(mets_xml, out_path)
    return format_new_file_info(volume_file_path, out_path, out_file)

def handle_boxes_file(volume_file_path, tempdir, storage_name):
    """
        Boxes file has "jp2" changed to "jpg", and is gzipped.
    """
    storage, out_path = single_file_setup(volume_file_path, tempdir, storage_name)

    # replace jp2 with jpg
    with storage.open(volume_file_path, "rb") as in_file:
        boxes_xml = in_file.read()
    boxes_xml = boxes_xml.replace(b'jp2', b'jpg')

    # write out xml
    write_xml_gz(boxes_xml, out_path)

def handle_md5_file(volume_file_path, tempdir, storage_name, new_digest):
    storage, out_path = single_file_setup(volume_file_path, tempdir, storage_name)

    with out_path.open('w') as out:
        out.write(new_digest)

def format_new_file_info(volume_file_path, out_path, out_file):
    return volume_file_path, {'new_path': str(out_path), 'digest':out_file.hexdigest(), 'length':out_file.length}

def single_file_setup(volume_file_path, tempdir, storage_name):
    info("processing %s" % volume_file_path)
    storage = get_storage(storage_name)  # start new connection for threads
    out_path = tempdir / volume_file_path
    out_path.parents[0].mkdir(parents=True, exist_ok=True)
    return storage, out_path

@shared_task
def compress_volume(storage_name, volume_name):
    storage, path_prefix = storage_lookup[storage_name]

    # only create archive if it doesn't already exist
    archive_name = "%s/%s/%s.tar" % (path_prefix, volume_name, volume_name)
    if settings.COMPRESS_VOLUMES_SKIP_EXISTING and captar_storage.exists(archive_name):
        info("%s already exists, returning" % volume_name)
        return

    # get sorted files
    volume_files_by_type = files_by_type(storage.iter_files_recursive(volume_name))

    # make a copy of volume in a temp dir
    with TemporaryDirectory() as tempdir:
        tempdir = Path(tempdir)
        volume_path = tempdir / volume_name
        volume_path.mkdir()

        # set up multithreading -- file_map function lets us run function in parallel across a list of file paths,
        # passing in tempdir along with each file path.
        if settings.COMPRESS_VOLUMES_THREAD_COUNT > 1:
            pool = ThreadPool(settings.COMPRESS_VOLUMES_THREAD_COUNT)
            mapper = pool.map
        else:
            mapper = map
        def file_map(func, files, *args, **kwargs):
            return list(mapper((lambda f: func(f, tempdir, storage_name, *args, **kwargs)), files))

        # store mapping of old paths to new paths and related md5 info
        new_file_info = {}
        def add_file_info(*info_lists):
            for info in info_lists:
                for k, v in info:
                    k = os.path.relpath(k, volume_name)
                    new_file_info[k] = v
                    v['new_path'] = os.path.relpath(v['new_path'], str(volume_path))

        # write alto, tif, and jpg files
        # use this if compressing tiff -> png
        # tif_file_results = file_map(handle_image_file, volume_files_by_type.get('tif', []), '.png', tif_to_png)
        file_map(handle_simple_file, volume_files_by_type.get('tif', []))
        file_map(handle_simple_file, volume_files_by_type.get('pdf', []))
        color_file_results = file_map(handle_image_file, volume_files_by_type.get('jp2', []), '.jpg', jp2_to_jpg_slow)
        # use this if compressing jp2 -> jp2
        # color_file_results = file_map(handle_image_file, volume_files_by_type.get('jp2', []), '.jp2', compress_jp2)
        alto_file_results = file_map(handle_alto_file, volume_files_by_type.get('alto', []))

        # write casemets files, using data gathered in previous step
        add_file_info(color_file_results, alto_file_results)
        case_file_results = file_map(handle_mets_file, volume_files_by_type.get('case', []), new_file_info, '../')

        # write volmets file, using data gathered in previous step
        add_file_info(case_file_results)
        new_volume_info = handle_mets_file(volume_files_by_type['volume'][0], tempdir, storage_name, new_file_info)

        # write volmets md5
        handle_md5_file(volume_files_by_type['md5'][0], tempdir, storage_name, new_volume_info[1]['digest'])

        # write boxes file
        if 'boxes' in volume_files_by_type:
            handle_boxes_file(volume_files_by_type['boxes'][0], tempdir, storage_name)

        # tar volume
        info("tarring %s" % volume_path)
        with tempfile.NamedTemporaryFile() as tar_out:
            # track hash of tar file
            tar_out = HashingFile(tar_out, hash_name='sha256')

            # track offsets of files in tar file
            tar = LoggingTarFile.open(fileobj=tar_out, mode='w|')

            # write files to temp tar file
            tar.add(str(volume_path), volume_name)
            tar.close()

            # write tar file to S3
            with open(tar_out.name, 'rb') as in_file:
                archive_name = captar_storage.save(archive_name, in_file)

            # write csv file to S3
            with captar_storage.open(archive_name+".csv", "w") as csv_out:
                csv_writer = csv.writer(csv_out)
                csv_writer.writerow(["path", "offset", "size"])
                for member in tar.members:
                    csv_writer.writerow([member.name, member.offset_data, member.size])

            # write sha256 file to S3
            with captar_storage.open(archive_name+".sha256", "w") as sha_out:
                sha_out.write(tar_out.hexdigest())

@contextmanager
def open_captar_volume(volume_path):
    with TemporaryDirectory() as temp_dir:
        # copy captar from S3 to disk if necessary
        if isinstance(captar_storage, CapS3Storage):
            Path(temp_dir, volume_path).mkdir(parents=True)
            for path in captar_storage.iter_files(str(volume_path)):
                copy_file(path, Path(temp_dir, path), from_storage=captar_storage)
            local_storage = CapFileStorage(temp_dir)
        else:
            local_storage = captar_storage

        try:
            volume_storage = CaptarStorage(local_storage, volume_path)
            assert volume_storage.index
        except (FileNotFoundError, AssertionError):
            yield None
        else:
            yield volume_storage

@shared_task
def validate_volume(volume_path):
    """
        Perform basic sanity checks on captar archives, and write "ok" or an error into `validation` folder.

        Relative to captar_storage:
            volume_path looks like 'redacted/32044031754302_redacted'
            output file looks like 'validation/redacted/32044031754302_redacted.txt'
    """

    # helpers
    top_level_file_sets = {("METS.md5", "METS.xml.gz"), ("BOXES.xml.gz", "METS.md5", "METS.xml.gz")}
    class ValidationResult(Exception):
        pass

    # check last result
    result_path = str(Path('validation', volume_path).with_suffix('.txt'))
    if captar_storage.exists(result_path):
        last_result = json.loads(captar_storage.contents(result_path))
        if last_result[0] == "ok":
            print("Volume %s already validated; skipping." % volume_path)
            return

    try:

        # load tar file as a storage wrapper and get list of items
        with open_captar_volume(volume_path) as volume_storage:
            if not volume_storage:
                raise ValidationResult("index_missing", "Failed to load index for %s" % volume_path)
            tar_items = set(volume_storage.iter_files_recursive(with_md5=True))

            # volmets_path is path with no slashes ending in METS.xml.gz
            volmets_path = next((item for item in tar_items if item[0].count("/") == 0 and item[0].endswith("METS.xml.gz")), None)

            # check for missing volmets
            if not volmets_path:
                raise ValidationResult("volmets_missing", volume_path)

            # check md5 of volmets
            md5_path = next((item[0] for item in tar_items if item[0].count("/") == 0 and item[0].endswith(".md5")), None)
            if not md5_path:
                raise ValidationResult("md5_missing")
            if volmets_path[1] != volume_storage.contents(md5_path):
                raise ValidationResult("volmets_md5_mismatch")

            # strip .gz so the storage will decompress for us
            volmets_path = volmets_path[0][:-3]

            # check for mismatched files
            orig_xml = volume_storage.contents(volmets_path)
            parsed = parse_xml(orig_xml)
            volmets_files = set(
                (
                    i.children('mets|FLocat').attr(resolve_namespace('xlink|href')),
                    i.attr('CHECKSUM')
                ) for i in parsed('mets|file').items()
            )

            # check that all files in METS are expected
            only_in_mets = volmets_files - tar_items
            if only_in_mets:
                raise ValidationResult("only_in_mets", only_in_mets)

            # check that all files only_in_tar are expected (should be one volmets and one volmets md5)
            only_in_tar = tuple(sorted(item[0].rsplit('_',1)[-1] for item in tar_items - volmets_files))
            if only_in_tar not in top_level_file_sets:
                raise ValidationResult("only_in_tar", only_in_tar)

            # count suffixes
            suffix_counts = defaultdict(int)
            for item in volmets_files:
                suffix_counts[item[0].split('.', 1)[1]] += 1
            color_image_count = suffix_counts['jpg'] or suffix_counts['pdf']
            if color_image_count == 0 or color_image_count != suffix_counts['tif'] or suffix_counts['xml.gz'] <= color_image_count:
                raise ValidationResult("unexpected_suffix_counts", suffix_counts)

            raise ValidationResult("ok")

    except ValidationResult as result:
        print(result.args)
        captar_storage.save(result_path, BytesIO(json.dumps(result.args).encode()))

def report_sizes():
    """
        Test function to find out size breakdown of files.
    """
    size_counts = defaultdict(int)
    suffix_counts = defaultdict(int)
    for index_path in captar_storage.iter_files_recursive():
        if not index_path.endswith('.csv'):
            continue
        file_list = csv.DictReader(captar_storage.contents(index_path).split("\n"))
        for item in file_list:
            size = int(item['size'])
            if size:
                suffix = item['path'].split('.', 1)[1]
                size_counts[suffix] += size
                suffix_counts[suffix] += 1
    total_size = sum(size_counts.values())
    print("Total size: %s" % total_size)
    for suffix, size in size_counts.items():
        print("- {}: {} files, {}, {:.1%}".format(suffix, suffix_counts[suffix], filesizeformat(size), size/total_size))


def sample_images(count=100):
    """
        Test function to sample random images from ingest.
    """
    import random
    from capdb.storages import private_ingest_storage
    def get_volumes():
        """ Get all up-to-date volumes. """
        volumes = private_ingest_storage.iter_files("")
        current_vol = next(volumes, "")
        while current_vol:
            next_vol = next(volumes, "")
            if volume_barcode_from_folder(current_vol) != volume_barcode_from_folder(next_vol):
                yield current_vol
            current_vol = next_vol

    print("Loading volumes to sample")
    volumes = list(get_volumes())
    for vol in random.sample(volumes, min(len(volumes), count)):
        print("Sampling", vol)
        id = volume_barcode_from_folder(vol)
        for i in [0,1]:
            img_name = "%s_00050_%s.tif" % (id, i)
            copy_file(
                Path(vol, "images", img_name),
                Path('sample_images_private_tif', img_name),
                from_storage=private_ingest_storage,
                to_storage=captar_storage)
