Capstone Scripts
================

This repo collects scripts to build and interact with the Capstone caselaw database.

Design
------

Capstone is a Postgresql database that captures all text data created from the Caselaw Access Project
in one location.

It stores several kinds of data:

* Original XML data
* Normalized metadata extracted from the XML (TODO)
* External metadata, such as the Reporter database (TODO)
* Changelog data, tracking changes and corrections (TODO)

The general philosophy is *progressive enhancement*. We start with a simple document store where
each table is just a long list of XML documents, and then build relational database features around
it.

Setup Requirements
------------------

Capstone is developed with Python 3. Requirements are installed with `pip`. Example install:

    $ mkvirtualenv -p python3 capstone
    (capstone)$ pip install -r requirements.txt

For local development, you should have postgres installed.

Alternatively, use the Vagrant development environment: install [Vagrant](https://www.vagrantup.com/downloads.html) (currently 1.9.3), run

    $ vagrant plugin install vagrant-vbguest
	$ vagrant up

and ask your devops engineer to accept and provision the new dev box before running

    $ vagrant ssh

Copy settings.example.py to settings.py and enter credentials to connect to postgres.

Run `alembic upgrade head` to load initial tables.

Scripts
-------

* **models.py**: Sqlalchemy definitions of the database schema.
* **create_tables.py**: Create tables from the models.py schema.
* **ingest_files.py**: Ingest XML files from s3 and/or from the ftl-sandbox copy.
* **process_ingested_xml.py**: Extract data from xml already loaded into DB.
* **set_up_postgres.py**: Write stored SQL functions to postgresql, and other functions for setting the postgres environment.
* **make_viz.py**: Write a visualization of the database to a 
  [public dashboard](https://harvard-ftl-public.s3.amazonaws.com/capstone/capstone.html). 
  This is currently run once per hour.
* **set_up_postgres.py**: Scripts to set up the postgres environment.

Environment
-----------

Capstone currently expects to run on `ftl-sandbox`, meaning it can:

* find a copy of the CAP volume/casemets files in `/ftldata/harvard-ftl-shared`
* view S3 mounts in `/mnt/`

Applying model changes
----------------------

Use `alembic` to apply migrations. After you change `models.py`:

    (capstone)$ alembic revision --autogenerate -m "Description of changes"
    
This will write a migration script to `alembic/versions`. Review the script and make sure it is correct!

Then apply:

    (capstone)$ alembic upgrade head
    
Stored Postgres functions
-------------------------

Some Capstone features depend on stored functions that allow Postgres to deal with XML and JSON fields.
See `set_up_postgres.py` for documentation.
