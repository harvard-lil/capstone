# tests to make sure our source repo is consistent, and no build commands need to be run
import os
import subprocess
from pathlib import Path
import pytest
from io import StringIO

from django.core import management

@pytest.mark.django_db
def test_makemigrations():
    out = StringIO()
    management.call_command('makemigrations', dry_run=True, stdout=out)
    assert out.getvalue() == 'No changes detected\n', "Model changes detected. Please run ./manage.py makemigrations"

def test_pip_compile():
    result = subprocess.run(["pip-compile", "-n"], stdout=subprocess.PIPE,
                            # strip COV_ environment variables so pip-compile doesn't try to report test coverage
                            env={k:v for k,v in os.environ.items() if not k.startswith('COV_')})
    existing_requirements = Path('requirements.txt').read_bytes()
    assert result.stdout == existing_requirements, "Changes detected to requirements.in. Please run pip-compile"

def test_flake8():
    subprocess.check_call('flake8')