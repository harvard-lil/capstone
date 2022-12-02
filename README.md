Capstone
========

[![test status](https://github.com/harvard-lil/capstone/actions/workflows/tests.yml/badge.svg)](https://github.com/harvard-lil/capstone/actions) [![codecov](https://codecov.io/gh/harvard-lil/capstone/branch/develop/graph/badge.svg)](https://codecov.io/gh/harvard-lil/capstone)

This is the source code for [case.law](https://case.law), a website written by the Harvard Law School Library Innovation Lab to manage and serve court opinions. Other than several cases used for our automated testing, this repository does not contain case data. Case data may be obtained through the website.

- [Capstone](#capstone)
  - [Project Background ](#project-background-)
  - [The Data ](#the-data-)
    - [Format Documentation and Samples ](#format-documentation-and-samples-)
    - [Obtaining Real Data ](#obtaining-real-data-)
    - [Reporting Data Errors ](#reporting-data-errors-)
    - [Errata ](#errata-)
  - [The Capstone Application ](#the-capstone-application-)
  - [Installing Capstone and CAPAPI ](#installing-capstone-and-capapi-)
    - [Hosts Setup ](#hosts-setup-)
    - [Docker Setup ](#docker-setup-)
  - [Administering and Developing Capstone ](#administering-and-developing-capstone-)
    - [Testing ](#testing-)
    - [Requirements ](#requirements-)
    - [Applying model changes ](#applying-model-changes-)
    - [Stored Postgres functions ](#stored-postgres-functions-)
    - [Running Command Line Scripts ](#running-command-line-scripts-)
    - [Logging In ](#logging-in-)
    - [Local debugging tools ](#local-debugging-tools-)
    - [Model versioning ](#model-versioning-)
    - [Download real data locally ](#download-real-data-locally-)
    - [Working with javascript ](#working-with-javascript-)
    - [Elasticsearch ](#elasticsearch-)
  - [Code examples ](#code-examples-)

## Project Background <a id="project-background"></a>
The Caselaw Access Project is a large-scale digitization project hosted by the Harvard Law School [Library Innovation Lab.](http://lil.law.harvard.edu "LIL Website") Visit [case.law](https://case.law/) for more details.

## The Data <a id="the-data"></a>
1. [Format Documentation and Samples](#documentation-and-samples)
2. [Obtaining Real Data](#obtaining-real-data)
3. [Reporting Data Errors](#reporting-data-errors)
4. [Errata](#errata)

### Format Documentation and Samples <a id="documentation-and-samples"></a>
The output of the project consists of page images, marked up case XML files, ALTO XML files, and METS XML files. This repository has a more detailed explanation of the format, and two volumes worth of sample data:

[CAP Samples and Format Documentation](https://github.com/harvard-lil/CAP_Sample_Volumes_Arkansas/tree/master/32044078573896_redacted)


### Obtaining Real Data <a id="obtaining-real-data"></a>
This data, with some temporary restrictions, is available to all. Please see our project site with more information about how to access the API, or get bulk access to the data:

https://case.law/


### Reporting Data Errors <a id="reporting-data-errors"></a>
This is a living, breathing corpus of data. While we've taken great pains to ensure its accuracy and integrity, two large components of this project, namely OCR and human review, are utterly fallible. When we were designing Capstone, we knew that one of its primary functions would be to facilitate safe, accountable updates. If you find any errors in the data, we would be extraordinarily grateful for your taking a moment to create an issue in this GitHub repository's issue tracker to report it. If you notice a large pattern of problems that would be better fixed programmatically, or have a very large number of modifications, describe it in an issue. If we need more information, we'll ask. We'll close the issue when the issue has been corrected.

### Errata <a id="errata"></a>
These are known issues — there's no need to file an issue if you come across one of these. 
- Missing Judges Tag: In many volumes, elements which should have the tag name `<judges>` instead have the tag name `<p>`. We're working on this one.
- Nominative Case Citations: In many cases that come from nominative volumes, the citation format is wrong. We hope to have this corrected soon.
- Jurisdictions: Though the jurisdiction values in our API metadata entries are normalized, we have not propagated those changes to the XML.
- Court Name: We've seen some inconsistencies in the court name. We're trying to get this normalized in the data, and we'll also publish a complete court name list when we're done.
- OCR errors: There will be OCR errors on nearly every page. We're still trying to figure out how best to address this. If you've got some killer OCR correction strategies, get at us.

## The Capstone Application <a id="the-capstone-application"></a>

Capstone is a Django application with a PostgreSQL database which stores and manages the non-image data output of the CAP project. This includes:

* Original XML data
* Normalized metadata extracted from the XML
* External metadata, such as the Reporter database
* Changelog data, tracking changes and corrections

## Installing Capstone and CAPAPI <a id="installing-capstone-and-capapi"></a>

### Hosts Setup <a id="hosts-setup"></a>

Add the following to `/etc/hosts`:

    127.0.0.1       case.test
    127.0.0.1       api.case.test
    127.0.0.1       cite.case.test

### Docker Setup <a id="docker-setup"></a>

We support local development via `docker compose`. Docker setup looks like this:

Using `pull` first will avoid rebuilding images locally:

    $ docker-compose pull

Start docker:

    $ docker-compose up -d

Set up databases:

    $ docker-compose exec db psql --user=postgres -c "CREATE DATABASE capdb;"
    $ docker-compose exec db psql --user=postgres -c "CREATE DATABASE capapi;"
    $ docker-compose exec db psql --user=postgres -c "CREATE DATABASE cap_user_data;"

Log into web container:

    $ docker-compose exec web bash
    # 

From now on all commands starting with `#` are assumed to be run from within `docker-compose exec web bash`.

Load dev data:

> ⚠️ **Note:** Make sure that Docker has sufficient resources allocated to run Elastic Search. Lower allocations may cause `rebuild_search_index` to crash.
> _Recommended minimum:_
> - CPUs: 6
> - Memory: 10 GB
> - Swap: 1 GB
> - Disk image: ~256 GB

    # fab init_dev_db
    # fab ingest_fixtures
    # fab import_web_volumes
    # fab refresh_case_body_cache
    # fab rebuild_search_index

To get ngrams working, run:

    # mkdir test_data/ngrams
    # fab ngram_jurisdictions

Run the dev server:

    # fab run
    
Capstone should now be running at 127.0.0.1:8000.

If you are working on javascript files, frontend, use `fab run_frontend`:
    
    # fab run_frontend

## Administering and Developing Capstone <a id="administering-and-developing-capstone"></a>
    - [Testing ](#testing-)
    - [Requirements ](#requirements-)
    - [Applying model changes ](#applying-model-changes-)
    - [Stored Postgres functions ](#stored-postgres-functions-)
    - [Running Command Line Scripts ](#running-command-line-scripts-)
    - [Logging In ](#logging-in-)
    - [Local debugging tools ](#local-debugging-tools-)
    - [Model versioning ](#model-versioning-)
    - [Download real data locally ](#download-real-data-locally-)
    - [Working with javascript ](#working-with-javascript-)
    - [Elasticsearch ](#elasticsearch-)

### Testing <a id="testing"></a>

We use pytest for tests. Some notable flags:

Run all tests:

    # pytest

Run one test:

    # pytest -k test_name

Drop into pdb on test failure:

    # pytest --pdb

Run tests in parallel for speed:

    # pytest -n 2

### Requirements <a id="requirements"></a>

Top-level requirements are stored in `requirements.in`. After updating that file, you should run

    # fab pip_compile

to freeze all subdependencies into `requirements.txt`.

To upgrade a single requirement to the latest version:

    # fab pip_compile:"-P package_name"

### Applying model changes <a id="applying-model-changes"></a>

Use Django to apply migrations. After you change `models.py`:

    # ./manage.py makemigrations

This will write a migration script to `cap/migrations`. Then apply:

    # fab migrate

This will migrate the underlying model in PostgreSQL. In order to transfer changes to Elasticsearch, apply:

    # fab rebuild_search_index
    
Ensure that the relevant handlers to transfer this data are written in capstone/capapi/documents.py.

### Stored Postgres functions <a id="stored-postgres-functions"></a>

Some Capstone features depend on stored functions.
See `set_up_postgres.py` for documentation.

### Running Command Line Scripts <a id="running-command-line-scripts"></a>

Command line scripts are defined in `fabfile.py`. You can list all available commands using `fab -l`, and run a
command with `fab command_name`.

### Logging In <a id="logging-in"></a>

`fab init_dev_db` will create a user with email `admin@example.com` and password `Password2`.

You can create additional test users from `./manage.py shell_plus` using the same code that is used by the `init_dev_db`
command, or using the web frontend on the local development server.

Creating a new user through the frontend requires access to an email verification link. That link will be shown in the 
output of `fab run` or `fab run_frontend` in the following format:

```
Content-Type: text/plain; charset="utf-8"
MIME-Version: 1.0
Content-Transfer-Encoding: 7bit
Subject: Caselaw Access Project: Verify your email address
From: info@example.com
To: a@mail.com
Date: Wed, 04 Aug 2021 17:53:46 -0000
Message-ID: <162809962609.2188.6020186441304370023@63fceca6d616>

Please click here to verify your email address:

https://case.test:8000/user/verify-user/4/ffffffffffffffffff/

If you received this message in error, please ignore it.
```

### Local debugging tools <a id="local-debugging-tools"></a>
[django-extensions](https://github.com/django-extensions/django-extensions) is enabled by default, including the very
handy `./manage.py shell_plus` command.

[django-debug-toolbar](https://django-debug-toolbar.readthedocs.io/en/stable/) is not automatically enabled, but if you
run `pip install django-debug-toolbar` it will be detected and enabled by `settings_dev.py`.

### Model versioning <a id="model-versioning"></a>
For database versioning we use the Postgres temporal tables approach inspired by SQL:2011's temporal databases.

See [this blog post](http://clarkdave.net/2015/02/historical-records-with-postgresql-and-temporal-tables-and-sql-2011/)
for an explanation of temporal tables and how to use them in Postgres. 

We use [django-simple-history](https://django-simple-history.readthedocs.io/en/latest/) to manage creation, migration,
and querying of the historical tables.

Data is kept in sync through the [temporal_tables](https://github.com/arkhipov/temporal_tables) Postgres extension
and the triggers created in our scripts/set_up_postgres.py file.

### Download real data locally <a id="download-real-data-locally"></a>

We store complete fixtures for about 1,000 cases in the case.law [downloads section](https://case.law/download/developer/).

You can download and ingest all volume fixtures from that section with the command `fab import_web_volumes`,
or ingest a single volume downloaded from that section with the command `fab import_volume:some.zip`.  

### Working with javascript <a id="working-with-javascript"></a>

We use Vite to compile javascript files. New javascript entrypoints can be added to vite.config.js and
included in templates with `{% vite_asset %}`.

To see javascript changes live, run the dev server with

    # fab run_frontend

This will start `yarn serve` behind the scenes before calling `fab run`.

### Elasticsearch <a id="elasticsearch"></a>

For local dev, Elasticsearch will automatically be started by `docker-compose up -d`. You can then run
`fab refresh_case_body_cache` to populate CaseBodyCache for all cases, and `fab rebuild_search_index` to populate the
search index.

For debugging, see settings.py.example for an example of how to log all requests to and from Elasticsearch.

It may also be useful to run Kibana to directly query Elasticsearch from a browser GUI:

    $ brew install kibana
    $ kibana -e http://127.0.0.1:9200

You can then go to Kibana -> Dev Tools to run any of the logged queries, or `GET /_mapping` to see the search indexes.

## Code examples <a id="examples"></a>
We maintain a separate [CAP examples repo](https://github.com/harvard-lil/cap-examples) for some ideas about 
using code to interact with CAP data.
