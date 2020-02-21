# tests to make sure our source repo is consistent, and no build commands need to be run
import os
import subprocess
from pathlib import Path

import fabfile
import pytest
from io import StringIO

from django.conf import settings
from django.core import management

from test_data.test_fixtures.helpers import dir_hash, file_hash


@pytest.mark.django_db
def test_makemigrations():
    out = StringIO()
    management.call_command('makemigrations', dry_run=True, stdout=out)
    assert out.getvalue() == 'No changes detected\n', "Model changes detected. Please run ./manage.py makemigrations"

def test_pip_compile__parallel():
    existing_requirements = Path('requirements.txt').read_bytes()
    subprocess.check_call(["fab", "pip-compile"], stdout=subprocess.PIPE,
                          # strip COV_ environment variables so pip-compile doesn't try to report test coverage
                          env={k:v for k,v in os.environ.items() if not k.startswith('COV_')})
    new_requirements = Path('requirements.txt').read_bytes()
    assert new_requirements == existing_requirements, "Changes detected to requirements.in. Please run fab pip-compile"

def test_flake8__parallel():
    subprocess.check_call('flake8')

@pytest.mark.skipif(not os.environ.get('DOCKERIZED'), reason="npm build can only be tested in docker")
def test_npm_build__parallel():
    dist_dir = Path(settings.STATICFILES_DIRS[0], settings.WEBPACK_LOADER['DEFAULT']['BUNDLE_DIR_NAME'])
    stats_file = settings.WEBPACK_LOADER['DEFAULT']['STATS_FILE']

    dist_hash = dir_hash(dist_dir)
    stats_hash = file_hash(stats_file)

    subprocess.check_call(['yarn', 'build'])

    dist_hash2 = dir_hash(dist_dir)
    stats_hash2 = file_hash(stats_file)

    assert dist_hash == dist_hash2, "'yarn build' updated files in %s" % dist_dir
    assert stats_hash == stats_hash2, "'yarn build' updated %s" % stats_file

def test_docker_compose_version__parallel():
    docker_compose_path = Path(settings.BASE_DIR, 'docker-compose.yml')
    existing_docker_compose = docker_compose_path.read_text()
    fabfile.update_docker_image_version()
    assert docker_compose_path.read_text() == existing_docker_compose, "'fab update_docker_image_version' needed to be run."