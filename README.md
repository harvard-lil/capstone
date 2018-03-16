Capstone
========

[![Build Status](https://travis-ci.org/harvard-lil/capstone.svg?branch=develop)](https://travis-ci.org/harvard-lil/capstone) [![Coverage Status](https://coveralls.io/repos/github/harvard-lil/capstone/badge.svg?branch=develop)](https://coveralls.io/github/harvard-lil/capstone?branch=develop)

The Capstone caselaw database.

Design
------

Capstone is a Postgresql database that captures all text data created from the Caselaw Access Project
in one location.

It stores several kinds of data:

* Original XML data
* Normalized metadata extracted from the XML
* External metadata, such as the Reporter database
* Changelog data, tracking changes and corrections

The general philosophy is *progressive enhancement*. We start with a simple document store where
each table is just a long list of XML documents, and then build relational database features around
it.

Setup Requirements
------------------

(Also see alternate Docker setup requirements below.)

Capstone is developed with Python 3. Requirements are installed with `pip`.

Clone:

    $ git clone https://github.com/harvard-lil/capstone.git
    
You will need MySQL, Redis, and Postgres for Capstone.
- MySQL installation:
  `brew install mysql` or [with apt-get](https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-14-04)
- [Redis installation](https://redis.io/topics/quickstart)
- [Postgres installation](https://www.postgresql.org/download/)

Set up Python virtualenv:
    
    $ cd capstone/capstone  # move to Django subdirectory
    $ mkvirtualenv -p python3 capstone
    (capstone)$ pip install -r requirements.txt

From here on, the prompt **(capstone)$** means you are running inside the `capstone/` subdir with
the `capstone` virtualenv activated.


Set up a postgres database:

    (capstone)$ psql -c "CREATE DATABASE capstone;"
    (capstone)$ psql -c "CREATE DATABASE capapi;"
    (capstone)$ fab init_db  # one time -- set up database tables and development Django admin user, migrate databases
    (capstone)$ fab load_test_data  # load in our test data

Migrate databases:

    (capstone)$ fab migrate

Docker Setup
------------

We have initial support for local development via `docker compose`. Docker setup looks like this:

    $ docker-compose up &
    $ docker-compose exec db psql --user=postgres -c "CREATE DATABASE capstone;"
    $ docker-compose exec db psql --user=postgres -c "CREATE DATABASE capapi;"
    $ docker-compose exec web fab init_db
    $ docker-compose exec web fab load_test_data
    
Capstone should now be running at 127.0.0.1:8000.

These commands can be shorter with something like this in .bash_profile:

    alias d="docker-compose exec"
    alias dfab="d web fab"

Running Capstone Server
-----------------------
    
    (capstone)$ fab run      # start up Django server

Go to http://127.0.0.1:8000/ and log in as admin / admin

Testing
-------

We use pytest for tests. Some notable flags:

Run all tests:

    (capstone)$ pytest

Run one test:

    (capstone)$ pytest -k test_name
     
Run tests without capturing stdout, to allow debugging with pdb:

    (capstone)$ pytest -s
    
Run tests in parallel for speed:

    (capstone)$ pytest -n <number of processes>

Requirements
------------

Top-level requirements are stored in `requirements.in`. After updating that file, you should run

    (capstone)$ pip-compile
    
to freeze all subdependencies into `requirements.txt`.

To ensure that your environment matches `requirements.txt`, you can run

    (capstone)$ pip-sync
    
This will add any missing packages and remove any extra ones.

Applying model changes
----------------------

Use Django to apply migrations. After you change `models.py`:

    (capstone)$ ./manage.py makemigrations
    
This will write a migration script to `cap/migrations`. Then apply:

    (capstone)$ ./manage.py migrate
    
Stored Postgres functions
-------------------------

Some Capstone features depend on stored functions that allow Postgres to deal with XML and JSON fields.
See `set_up_postgres.py` for documentation.

Running Command Line Scripts
----------------------------

Command line scripts are defined in `fabfile.py`. You can list all available commands using `fab -l`, and run a
command with `fab command_name`.

Local debugging tools
---------------------

[django-extensions](https://github.com/django-extensions/django-extensions) is enabled by default, including the very
handy `./manage.py shell_plus` command.

[django-debug-toolbar](https://django-debug-toolbar.readthedocs.io/en/stable/) is not automatically enabled, but if you
run `pip install django-debug-toolbar` it will be detected and enabled by `settings_dev.py`.

Download real data locally 
--------------------------

To write test data and fixtures for given volume and case:
run the fab command `fab add_test_case` with a volume barcode
(like `fab add_test_case:32044057891608_0001`)
- In settings.py, you will need to point DATABASES['tracking_tool'] to the real tracking tool db
- You will also need to point STORAGES['ingest_storage'] to real harvard-ftl-shared


Model versioning
----------------

For database versioning we use the Postgres temporal tables approach inspired by SQL:2011's temporal databases.

See [this blog post](http://clarkdave.net/2015/02/historical-records-with-postgresql-and-temporal-tables-and-sql-2011/)
for an explanation of temporal tables and how to use them in Postgres. 

We use [django-simple-history](https://django-simple-history.readthedocs.io/en/latest/) to manage creation, migration,
and querying of the historical tables.

Data is kept in sync through the [temporal_tables](https://github.com/arkhipov/temporal_tables) Postgres extension
and the triggers created in our scripts/set_up_postgres.py file.

Installing the temporal_tables extension is recommended for performance. If not installed, a pure postgres version
will be installed by set_up_postgres.py; this is handy for development.

