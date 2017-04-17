{% set user = 'vagrant' %}
{% set home = '/home/vagrant' %}
{% set repo = '/vagrant' %}

jessie-backports:
  pkgrepo.managed:
    - name: deb http://ftp.debian.org/debian jessie-backports main

postgres-pkgs:
  pkg.installed:
    - fromrepo: jessie-backports
    - pkgs:
      - postgresql-9.6
      - libpq-dev

stretch:
  pkgrepo.managed:
    - name: deb http://ftp.debian.org/debian stretch main

plv8-pkgs:
  pkg.installed:
    - fromrepo: stretch
    - pkgs:
      - postgresql-9.6-plv8
    - require:
      - pkg: postgres-pkgs

capstone-pkgs:
  pkg.installed:
    - pkgs:
      - python3
      - python3-dev
      - virtualenv
      - virtualenvwrapper

venv-dir:
  file.directory:
    - name: {{ home }}/.virtualenvs
    - user: {{ user }}
    - group: {{ user }}

capstone-venv:
  virtualenv.managed:
    - name: {{ home }}/.virtualenvs/capstone
    - python: /usr/bin/python3
    - requirements: {{ repo }}/requirements.txt
    - user: {{ user }}
    - require:
      - pkg: capstone-pkgs
      - file: venv-dir

{{ home }}/.bashrc:
  file.append:
    - text: |
        # activate virtualenv
        export WORKON_HOME={{ home }}/.virtualenvs
        source /usr/share/virtualenvwrapper/virtualenvwrapper.sh
        workon capstone
        cd {{ repo }}
