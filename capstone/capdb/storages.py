import csv
import gzip
import hashlib
import os
import itertools
from pathlib import Path

import redis

from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.functional import SimpleLazyObject
from storages.backends.s3boto3 import S3Boto3Storage


class CapStorageMixin(object):
    def relpath(self, path):
        return os.path.relpath(path, self.location)

    def contents(self, path, mode='r'):
        """ Return full contents of file at path. """
        with self.open(path, mode) as f:
            result = f.read()
        return result

    def deconstruct(obj):
        """
            This is called by makemigrations when a FileField has storage= set.
            Hardcoding a value ensures that changing storage backend for different
            deployments doesn't result in a new migration.
        """
        return ("django.core.files.storage.FileSystemStorage", [], {})


class CapS3Storage(CapStorageMixin, S3Boto3Storage):
    def _fix_path(self, path):
        return self._encode_name(self._normalize_name(self._clean_name(path)))

    def iter_files(self, path="", partial_path=False):
        """
            Yield each immediate file or directory in path.

            If partial_path is True, returns files starting with path.
        """

        path = path.rstrip('/')

        # if not partial_path, prefix should end with a slash
        if path and not partial_path:
            path += '/'

        path = self._fix_path(path)

        paginator = self.connection.meta.client.get_paginator('list_objects_v2')
        pages = paginator.paginate(Bucket=self.bucket_name, Delimiter='/', Prefix=path)
        for page in pages:
            for item in page.get('CommonPrefixes', []):
                yield(self.relpath(item['Prefix'].rstrip('/')))
            for item in page.get('Contents', []):
                yield(self.relpath(item['Key']))

    def iter_files_recursive(self, path="", with_md5=False):
        """
            Yield each file in path or subdirectories.
            Order is not specified.
        """
        path = path.rstrip('/')
        if path:
            path += '/'  # should end with exactly one slash
        entries = self.bucket.objects.filter(Prefix=self._fix_path(path))
        if with_md5:
            return ((self.relpath(self._decode_name(entry.key)), entry.e_tag.strip('"')) for entry in entries)
        else:
            return (self.relpath(self._decode_name(entry.key)) for entry in entries)

    def tag_file(self, path, key, value):
        """ Tag S3 item at path with key=value. """
        results = self.connection.meta.client.put_object_tagging(
            Bucket=self.bucket_name,
            Key=path,
            Tagging={
                'TagSet': [
                    {
                        'Key': key,
                        'Value': value
                    }
                ]
            }
        )
        # boto3 should return 'versionID': (version id) if successful, this will return True or False
        return 'VersionId' in results

    def contents(self, path, mode='r'):
        result = super().contents(path, mode)

        # handle S3Boto3Storage bug where 'r' mode returns bytes -- https://github.com/jschneier/django-storages/issues/404
        if mode == 'r':
            result = result.decode('utf8')

        return result

    def delete_file(self, path):
        """ Delete S3 item at path. NEVER USE THIS. """
        results = self.connection.meta.client.delete_object(
            Bucket=self.bucket_name,
            Key=path
        )
        # boto3 should return 'versionID': (version id) if successful, this will return True or False
        return 'VersionId' in results


class CapFileStorage(CapStorageMixin, FileSystemStorage):

    def iter_files(self, search_path="", partial_path=False):
        """
            Yield each immediate file or directory in path.

            If partial_path is True, returns files starting with path.
        """
        if partial_path:
            search_path, prefix = os.path.split(search_path)

        directories, files = self.listdir(search_path)
        for file_name in itertools.chain(directories, files):
            if partial_path and not file_name.startswith(prefix):
                continue
            # skip hidden files starting with .
            if file_name.startswith('.'):
                continue
            yield os.path.join(search_path, file_name)

    def iter_files_recursive(self, path="", with_md5=False):
        """
            Yield each file in path or subdirectories.
            Order is not specified.
        """
        for root, dirs, file_names in os.walk(self.path(path)):
            for file_name in file_names:
                # skip hidden files starting with .
                if file_name.startswith('.'):
                    continue
                rel_path = self.relpath(os.path.join(root, file_name)).lstrip('/')
                if with_md5:
                    yield rel_path, hashlib.md5(self.contents(rel_path, 'rb')).hexdigest()
                else:
                    yield rel_path

    def tag_file(self, path, key, value):
        """ For file storage, tags don't work. """
        return False


class CaptarFile(File):
    """
        File wrapper used by CaptarStorage. This is a limit-offset file reader, which reads a subset of bytes from a
        larger file. For example:

            CaptarFile(BytesIO(b"Hey what's up"), offset=4, size=6).read() == b"what's"

        Inspired by https://github.com/webrecorder/warcio/blob/master/warcio/limitreader.py
    """

    def __init__(self, file, offset, size):
        super(CaptarFile, self).__init__(file)
        self.end = offset+size
        self.start = offset
        self.pos = offset
        file.seek(offset)

    def _update(self, buff):
        self.pos += len(buff)
        return buff

    def _safe_length(self, length):
        if length is not None:
            return min(length, self.end - self.pos)
        else:
            return self.end - self.pos

    def read(self, length=None):
        length = self._safe_length(length)

        if length == 0:
            return b''

        buff = self.file.read(length)
        return self._update(buff)

    def readline(self, length=None):
        length = self._safe_length(length)

        if length == 0:
            return b''

        buff = self.file.readline(length)
        return self._update(buff)

    def seek(self, pos):
        pos = max(self.start, min(self.end, pos))
        self.file.seek(pos)
        self.pos = pos


class CaptarStorage(CapStorageMixin, Storage):
    """
        This storage reads files from a CAPTAR volume, using the index CSV file. An example volume might be laid out like
        this:

            volume_name/volume_name.tar
            volume_name/volume_name.tar.csv:
                foo/entry1.jpg      offset  size
                foo/entry2.xml.gz   offset  size

        Example usage:

            volume_storage = CaptarStorage(parent_storage, "volume_name")
            print("JPG contents:", volume_storage.contents("foo/entry1.jpg"))
            print("Gzip contents:", volume_storage.contents("foo/entry2.xml.gz"))
            print("Automatically ungzipped contents:", volume_storage.contents("foo/entry2.xml"))
    """
    def __init__(self, parent, path):
        self.parent = parent
        self.path = path
        self.tar_path = str(Path(path, Path(path).name+".tar"))
        self.index_path = self.tar_path+".csv"
        self.index = {}
        for line in csv.DictReader(parent.contents(self.index_path).split("\n")):
            path = line["path"]
            if '/' not in path:
                continue
            path = path.split("/", 1)[1]  # remove top-level directory
            self.index[path] = line

    def contents(self, path, mode='r'):
        contents = super().contents(path, 'rb')
        if mode == 'r':
            contents = contents.decode()
        return contents

    def _open(self, name, mode):
        name = str(name)
        if name not in self.index:
            # if given a file name that doesn't exist, but where the name with .gz does exist,
            # return the ungzipped version
            gz_name = name+'.gz'
            if gz_name in self.index:
                gz_in = self._open(gz_name, "rb")
                return gzip.open(gz_in, mode)

            raise IOError('File does not exist: %s' % name)
        
        file_info = self.index[name]
        return CaptarFile(self.parent.open(self.tar_path, mode), int(file_info["offset"]), int(file_info["size"]))

    def iter_files(self, path="", partial_path=False):
        """
            Yield each immediate file or directory in path.

            If partial_path is True, returns files starting with path.
        """

        path = path.rstrip('/')

        # if not partial_path, prefix should end with a slash
        if path and not partial_path:
            path += '/'

        items = set(path+key[len(path):].split('/',1)[0] for key in self.index.keys() if key.startswith(path))
        for item in items:
            yield item

    def iter_files_recursive(self, path="", with_md5=False):
        """
            Yield each file in path or subdirectories.
            Order is not specified.
        """
        path = path.rstrip('/')
        if path:
            path += '/'  # should end with exactly one slash
        for key, info in self.index.items():
            if info["size"] != "0" and key.startswith(path):
                if with_md5:
                    yield key, hashlib.md5(self.contents(key, 'rb')).hexdigest()
                else:
                    yield key

### instances ###

# settings.py will define a list of storages like this:
#     STORAGES = {
#         'ingest_storage': {
#             'class': 'CapFileStorage',
#             'kwargs': {
#                 'location': os.path.join(BASE_DIR, 'test_data/from_vendor'),
#             },
#         },
#     }
# Based on the above setting, the following code does the equivalent of:
#     ingest_storage = CapFileStorage(location=os.path.join(BASE_DIR, 'test_data/from_vendor'))
# This allows code elsewhere to do `from capdb.storages import ingest_storage` and use the storages defined by settings.STORAGES

def get_storage(storage_name):
    """ Get a new instance of a storage by looking up its settings in settings.STORAGES. """
    storage_config = settings.STORAGES[storage_name]
    storage_class_name = storage_config['class']
    storage_class = globals_dict[storage_class_name]
    storage_class_kwargs = storage_config.get('kwargs', {})
    storage_instance = storage_class(**storage_class_kwargs)
    return storage_instance

globals_dict = globals()
for storage_name in settings.STORAGES:
    globals_dict[storage_name] = get_storage(storage_name)


### redis connections ###

redis_client = SimpleLazyObject(lambda: redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_DEFAULT_DB))
redis_ingest_client = SimpleLazyObject(lambda: redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=settings.REDIS_INGEST_DB))
