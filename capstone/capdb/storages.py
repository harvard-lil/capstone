import csv
import gzip
import hashlib
import traceback
from contextlib import contextmanager

import msgpack
import os
import itertools
from pathlib import Path

import redis
import rocksdb

from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.functional import SimpleLazyObject
from rocksdb.interfaces import MergeOperator
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
            Key=os.path.join(self.location, path),
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
            Key=os.path.join(self.location, path)
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
        self.hash_path = self.tar_path + '.sha256'
        self.index_path = self.tar_path+".csv"
        self.index = {}
        for line in csv.DictReader(parent.contents(self.index_path).split("\n")):
            path = line["path"]
            if '/' not in path:
                continue
            path = path.split("/", 1)[1]  # remove top-level directory
            self.index[path] = line

    def get_hash(self):
        """ Get contents of .sha256 file. """
        return self.parent.contents(self.hash_path)

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

    def exists(self, name):
        return str(name) in self.index or str(name)+'.gz' in self.index

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


### K/V stores ###

class KVDB:
    """ Base key-value store wrapper. """
    def __init__(self, path=settings.STORAGES['ngram_storage']['kwargs']['location'], name=None, read_only=False):
        self.path = path
        self.read_only = read_only
        if name:
            self.name = name

    @staticmethod
    def unpack(v, packed=True):
        return msgpack.unpackb(v) if packed and v is not None else v

    @staticmethod
    def pack(v, packed=True):
        return msgpack.packb(v) if packed and v is not None else v

    def open(self):
        raise NotImplementedError

    _db = None
    @property
    def db(self):
        """ Open database connection on first use. """
        if not self._db:
            self.open()
        return self._db


class NgramRocksDB(KVDB):
    """ Wrapper for RocksDB. """
    name = 'rocksdb'
    batch = None

    ## helpers

    def db_path(self):
        return os.path.join(self.path, self.name+".db")

    def open(self):
        # initial "production ready" settings via https://python-rocksdb.readthedocs.io/en/latest/tutorial/index.html
        opts = rocksdb.Options()
        opts.create_if_missing = True
        opts.max_open_files = 300000
        opts.write_buffer_size = 64 * 2**20  # 64MB
        opts.max_write_buffer_number = 3
        opts.target_file_size_base = 64 * 2**20  # 64MB
        opts.merge_operator = self.NgramMergeOperator()
        opts.compression = rocksdb.CompressionType.lz4_compression

        # fast ingest stuff
        # via https://github.com/facebook/rocksdb/wiki/RocksDB-FAQ -- "Q: What's the fastest way to load data into RocksDB?"
        # these settings require manual compaction after ingest
        opts.max_background_flushes = 8
        opts.level0_file_num_compaction_trigger = -1
        opts.level0_slowdown_writes_trigger = -1
        opts.level0_stop_writes_trigger = 2 ** 16  # default is 24 -- we want to avoid hitting this until it's done
        opts.write_buffer_size = 32 * 2**20  # default is 4 * 2 ** 20
        opts.max_write_buffer_number = 8  # default is 2

        opts.table_factory = rocksdb.BlockBasedTableFactory(
            filter_policy=rocksdb.BloomFilterPolicy(10),
            block_cache=rocksdb.LRUCache(2 * 2 ** 30),  # 2GB
            block_cache_compressed=rocksdb.LRUCache(500 * 2 ** 20))  # 500MB

        self._db = rocksdb.DB(self.db_path(), opts, read_only=self.read_only)

    def db_or_batch(self, batch=None):
        return batch or self.batch or self.db

    @contextmanager
    def in_transaction(self, *args, **kwargs):
        """
            This is not really a RocksDB transaction, which python-rocksdb doesn't seem to support, but a WriteBatch,
            which is effectively the same for write-only transactions that fit in RAM.
        """
        self.batch = rocksdb.WriteBatch(*args, **kwargs)
        try:
            yield self.batch
            self.db.write(self.batch)
        finally:
            self.batch = None

    ## writers

    def put(self, k, v, packed=False, batch=None):
        self.db_or_batch(batch).put(k, self.pack(v, packed))

    class NgramMergeOperator(MergeOperator):
        def full_merge(self, key, existing_value, ops):
            """
                Our mergable keys contain the counts for all jurisdiction-years and totals for an ngram, like this:
                    existing_value == self.pack({
                        <jurisdiction_id>: [
                            <year>, <instance_count>, <document_count>,
                            <year>, <instance_count>, <document_count>,
                            ...
                        ],
                        None: {
                            <year>: [<instance_count>, <document_count>],
                            ...,
                            None: [<instance_count>, <document_count>],
                        }
                    })
                This function merges in new observations, in the form:
                    ops == [
                        self.pack((<jurisdiction_id>, <year>, <instance_count>, <document_count>)),
                        ...
                    ]
            """
            try:
                # get target for merge
                value = KVDB.unpack(existing_value) if existing_value else {
                    None: {
                        None: [0, 0],
                    }
                }
                for new_value in ops:
                    # get values to merge
                    new_value = KVDB.unpack(new_value)
                    jurisdiction_id, storage_year, instance_count, document_count = new_value
                    # merge in individual jurisdiction-year value
                    value.setdefault(jurisdiction_id, []).extend((storage_year, instance_count, document_count))
                    # merge in running total for year
                    totals = value[None]
                    totals_year = totals.setdefault(storage_year, [0,0])
                    totals_year[0] += instance_count
                    totals_year[1] += document_count
                    # merge in running total for all years combined
                    total = totals[None]
                    total[0] += instance_count
                    total[1] += document_count
                return (True, KVDB.pack(value))
            except Exception:
                # rocksdb swallows this stack trace, so print before raising
                traceback.print_exc()
                raise

        def name(self):
            return b'ngram_merge'

    def merge(self, k, v, packed=False, batch=None):
        self.db_or_batch(batch).merge(k, self.pack(v, packed))

    ## readers

    def get(self, k, packed=False):
        return self.unpack(self.db.get(k), packed)

    def get_prefix(self, prefix, packed=False):
        it = self.db.iteritems()
        it.seek(prefix)
        for k, v in it:
            if not k.startswith(prefix):
                return
            yield k, self.unpack(v, packed)

# using SimpleLazyObject lets our tests mock the wrapped object after import
ngram_kv_store = SimpleLazyObject(lambda: NgramRocksDB())
ngram_kv_store_ro = SimpleLazyObject(lambda: NgramRocksDB(read_only=True))