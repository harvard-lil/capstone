Capstone Scripts
================

This repo collects scripts to build and interact with the Capstone caselaw database.

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

Capstone is developed with Python 3. Requirements are installed with `pip`.

Clone:

    $ git clone https://github.com/harvard-lil/capstone.git
    
Set up Python virtualenv:
    
    $ cd capstone/capstone  # move to Django subdirectory
    $ mkvirtualenv -p python3 capstone
    (capstone)$ pip install -r requirements.txt

From here on, the prompt **(capstone)$** means you are running inside the `capstone/` subdir with
the `capstone` virtualenv activated.

[Download and install Postgres](https://www.postgresql.org/download/), if necessary.

Set up a postgres database:

    (capstone)$ psql -c "CREATE DATABASE capstone;"
    (capstone)$ psql -c "CREATE DATABASE capapi;"
    (capstone)$ fab init_db  # one time -- set up database tables and development Django admin user
    (capstone)$ fab load_test_data  # load in our test data

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