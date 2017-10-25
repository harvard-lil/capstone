from io import BytesIO
import pytest
from moto import mock_s3

from ..storages import CapS3Storage, CapFileStorage


@pytest.fixture
def s3_storage():
    with mock_s3():
        yield CapS3Storage(
            auto_create_bucket=True,
            bucket_name='bucket',
            location='subdir',
        )

@pytest.fixture
def file_storage(tmpdir):
    return CapFileStorage(location=str(tmpdir))

def test_iter_files_s3_storage(s3_storage):
    base_test_iter_files(s3_storage)

def test_iter_files_file_storage(file_storage):
    base_test_iter_files(file_storage)

def base_test_iter_files(storage):
    # create test files
    sub_dir = ['d/e/f.txt', 'd/g/h.txt']
    file_names = ['a/b.txt', 'c.txt'] + sub_dir
    for file_name in file_names:
        storage.save(file_name, BytesIO(b'content'))

    # list files
    assert {'a', 'd', 'c.txt'} == set(storage.iter_files())
    assert {'d/e', 'd/g'} == set(storage.iter_files('d'))

    # list files with partial_path
    assert {'a/b.txt'} == set(storage.iter_files('a/b.', partial_path=True))

    # list files recursively
    assert set(file_names) == set(storage.iter_files_recursive())
    assert set(sub_dir) == set(storage.iter_files_recursive('d'))

