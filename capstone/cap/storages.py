import os

from django.core.files.storage import FileSystemStorage
from storages.backends.s3boto3 import S3Boto3Storage

class CapStorageMixin(object):
    def relpath(self, path):
        return os.path.relpath(path, self.location)

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
        paginator = self.connection.meta.client.get_paginator('list_objects')
        for result in paginator.paginate(Bucket=self.bucket_name, Prefix=self._fix_path(path), Delimiter='/'):
            for prefix in result.get('CommonPrefixes', []):
                yield(self.relpath(prefix.get('Prefix').rstrip('/')))

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