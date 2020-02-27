from io import BytesIO


def test_iter_files_s3_storage__parallel(s3_storage):
    base_test_iter_files(s3_storage)

def test_iter_files_file_storage__parallel(file_storage):
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


def test_isfile__parallel(file_storage):
    file_names = ['a/b.txt', 'c.txt']
    for file_name in file_names:
        file_storage.save(file_name, BytesIO(b'content'))

    assert file_storage.isfile('a/b.txt')
    assert file_storage.isfile('c.txt')

    assert not file_storage.isfile('a')


def test_isdir__parallel(file_storage):
    file_storage.save('a/b.txt', BytesIO(b'content'))

    assert file_storage.isdir('a')
    assert not file_storage.isdir('a/b.txt')
