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

def test_docker_compose_version__parallel():
    docker_compose_path = Path(settings.BASE_DIR, 'docker-compose.yml')
    existing_docker_compose = docker_compose_path.read_text()
    fabfile.update_docker_image_version()
    assert docker_compose_path.read_text() == existing_docker_compose, "'fab update_docker_image_version' needed to be run."
