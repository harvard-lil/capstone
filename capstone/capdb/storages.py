import os
import redis

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage

class CapStorageMixin(object):
    def relpath(self, path):
        return os.path.relpath(path, self.location)

    def contents(self, path, mode='r'):
        """ Return full contents of file at path. """
        with self.open(path, mode) as f:
            result = f.read()
        return result

class CapS3Storage(CapStorageMixin, S3Boto3Storage):
    def _fix_path(self, path):
        return self._encode_name(self._normalize_name(self._clean_name(path)))

    def iter_files(self, path=""):
        """
            Return iterator with all files within given path or subdirectories. 
            Path should be relative to root for this storage.
            Order is not specified.
        """
        return (self.relpath(self._decode_name(entry.key)) for entry in self.bucket.objects.filter(Prefix=self._fix_path(path)))

    def iter_subdirs(self, path=""):
        """
            Yield each immediate subdirectory in path.  
        """
        
        if path:
            path = path.rstrip('/')+'/'  # exactly one slash on right

        paginator = self.connection.meta.client.get_paginator('list_objects')
        for result in paginator.paginate(Bucket=self.bucket_name, Prefix=self._fix_path(path), Delimiter='/'):
            for prefix in result.get('CommonPrefixes', []):
                yield(self.relpath(prefix.get('Prefix').rstrip('/')))

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

class CapFileStorage(CapStorageMixin, FileSystemStorage):
    def iter_files(self, path=""):
        """
            Return iterator with all files within given path or subdirectories. 
            Path should be relative to root for this storage.
            Order is not specified.
        """
        return (self.relpath(os.path.join(root, file_name)).lstrip('/')
                for root, dirs, file_names in os.walk(self.path(path))
                for file_name in file_names)

    def iter_subdirs(self, path=""):
        """
            Yield each immediate subdirectory in path.  
        """
        directories, files = self.listdir(path)
        for subdir in directories:
            yield os.path.join(path, subdir)

    def tag_file(self, path, key, value):
        """ For file storage, tags don't work. """
        return False


### instances ###

# settings.py will define a list of storages like this:
# STORAGES = {
#     'ingest_storage': {
#         'class': 'CapFileStorage',
#         'kwargs': {
#             'location': os.path.join(BASE_DIR, 'test_data/from_vendor'),
#         },
#     },
# }

# Based on the above setting, the following code does the equivalent of:
#   ingest_storage = CapFileStorage(location=os.path.join(BASE_DIR, 'test_data/from_vendor'))
# This allows code elsewhere to do `from capdb.storages import ingest_storage` and use the storages defined by settings.STORAGES

globals_dict = globals()
for storage_name, storage_config in settings.STORAGES.items():
    storage_class_name = storage_config['class']
    storage_class = globals_dict[storage_class_name]
    storage_class_kwargs = storage_config.get('kwargs', {})
    storage_instance = storage_class(**storage_class_kwargs)
    globals_dict[storage_name] = storage_instance


### redis connection ###

redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT)