import hashlib
from pathlib import Path


def file_hash(path):
    """
        Return md5 hash of file contents.
    """
    return hashlib.md5(Path(path).read_bytes()).hexdigest()

def dir_hash(directory):
    """
        Return single md5 hash of all filenames and file contents in directory, for comparison.
    """
    hash = hashlib.md5()
    path = Path(directory)

    if not path.exists():
        raise FileNotFoundError

    for file in sorted(path.glob('**/*')):
        hash.update(bytes(str(file), 'utf8'))
        if file.is_file():
            hash.update(file.read_bytes())

    return hash.hexdigest()