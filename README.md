Capstone
========

[![CircleCI](https://circleci.com/gh/harvard-lil/capstone.svg?style=svg)](https://circleci.com/gh/harvard-lil/capstone) [![codecov](https://codecov.io/gh/harvard-lil/capstone/branch/develop/graph/badge.svg)](https://codecov.io/gh/harvard-lil/capstone)

This is the source code for [case.law](https://case.law), a website written by the Harvard Law School Library Innovation Lab to manage and serve court opinions. Other than several cases used for our automated testing, this repository does not contain case data. Case data may be obtained through the website.

- [Project Background](#project-background)
- [The Data](#the-data)
  - [Format Documentation and Samples](#documentation-and-samples)
  - [Obtaining Real Data](#obtaining-real-data)
  - [Reporting Data Errors](#reporting-data-errors)
  - [Errata](#errata)
- [The Capstone Application](#the-capstone-application)
- [CAPAPI](#capapi)
- [Installing Capstone and CAPAPI](#installing-capstone-and-capapi)
  - [Hosts Setup](#hosts-setup)
  - [Manual Local Setup](#manual-local-setup)
    - [Install global system requirements](#install-global-system-requirements)
    - [Clone the repository](#clone-the-repository)
    - [Set up python virtualenv](#set-up-Python-virtualenv)
    - [Install application requirements](#install-application-requirements)
    - [Set up the postgres database and load test data](#set-up-the-postgres-database-and-load-test-data)
    - [Running the capstone server](#running-the-capstone-server)
  - [Docker Setup](#docker-setup)
- [Administering and Developing Capstone](#administering-and-developing-capstone)
  - [Testing](#testing)
  - [Requirements](#requirements)
  - [Applying model changes](#applying-model-changes)
  - [Stored Postgres functions](#stored-postgres-functions)
  - [Running Command Line Scripts](#running-command-line-scripts)
  - [Local debugging tools](#local-debugging-tools)
  - [Download real data locally](#download-real-data-locally )
  - [Model versioning](#model-versioning)
  - [Working with javascript](#working-with-javascript)
  - [Elasticsearch](#elasticsearch)
- [Documentation](#documentation)
- [Examples](#examples)

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

## CAPAPI <a id="capapi"></a>
CAPAPI is the API with which users can access CAP data.

## Installing Capstone and CAPAPI <a id="installing-capstone-and-capapi"></a>
- [Manual Local Setup](#manual-local-setup)
- [Docker Setup](#docker-setup)

### Hosts Setup <a id="hosts-setup"></a>

Add the following to `/etc/hosts`:

    127.0.0.1       case.test
    127.0.0.1       api.case.test
    127.0.0.1       cite.case.test

### Manual Local Setup <a id="manual-local-setup"></a>
1. [Install global system requirements](#install-global-system-requirements)
2. [Clone the repository](#clone-the-repository)
3. [Set up python virtualenv](#set-up-Python-virtualenv)
4. [Install application requirements](#install-application-requirements)
5. [Set up the postgres database and load test data](#set-up-the-postgres-database-and-load-test-data)
6. [Running the capstone server](#running-the-capstone-server)


#### 1. Install global system requirements <a id="install-global-system-requirements"></a>
- **Python 3.5.4**— While there shouldn't be any issues with using a more recent version, we will only accept PRs that are fully compatible with 3.5.4.
- **MySQL**— On Macs with homebrew, the version installed with `brew install mysql` works fine. On Linux, [apt-get](https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-14-04) does the job
- **Redis**— ([Instructions](https://redis.io/topics/quickstart))
- **Postgres > 9.5**— ([Instructions](https://www.postgresql.org/download/))
For Mac developers, [Postgres.app](https://postgresapp.com/) is a nice, simple way to get an instant postgres dev installation.
- **Git**— ([Instructions](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git))


#### 2. Clone the repository <a id="clone-the-repository"></a>

    $ git clone https://github.com/harvard-lil/capstone.git

#### 3. Set up Python virtualenv (optional) <a id="set-up-Python-virtualenv"></a>

    $ cd capstone/capstone  # move to Django subdirectory
    $ mkvirtualenv -p python3 capstone

#### 4. Install application requirements <a id="install-application-requirements"></a>
    (capstone)$ pip install -r requirements.txt

This will make a virtualenv entitled "capstone." You can tell that you're inside the virtualenv because your shell prompt will now include the string **(capstone)**.

#### 5. Set up the postgres database and load test data <a id="set-up-the-postgres-database-and-load-test-data"></a>

    (capstone)$ psql -c "CREATE DATABASE capdb;"
    (capstone)$ psql -c "CREATE DATABASE capapi;"
    (capstone)$ psql -c "CREATE DATABASE cap_user_data;"
    (capstone)$ fab init_dev_db  # one time -- set up database tables and development Django admin user, migrate databases
    (capstone)$ fab load_test_data  # load in our test data
    (capstone)$ fab update_all_snippets  # make our pre-generated data snippets 

#### 6. Running the capstone server <a id="running-the-capstone-server"></a>

    (capstone)$ fab run      # start up Django server

Capstone should now be running at 127.0.0.1:8000.

### Docker Setup <a id="docker-setup"></a>

We have initial support for local development via `docker compose`. Docker setup looks like this:

    $ docker-compose up -d
    $ docker-compose exec db psql --user=postgres -c "CREATE DATABASE capdb;"
    $ docker-compose exec db psql --user=postgres -c "CREATE DATABASE capapi;"
    $ docker-compose exec db psql --user=postgres -c "CREATE DATABASE cap_user_data;"
    $ docker-compose exec web fab init_dev_db
    $ docker-compose exec web fab load_test_data
    $ docker-compose exec web fab update_all_snippets
    $ docker-compose exec web fab run
    
Capstone should now be running at 127.0.0.1:8000.

If you are working on frontend, you probably want to run yarn as well.
In a new shell:
    
    $ docker-compose exec web yarn serve


***Tip***— these commands can be shortened by adding something like this to .bash_profile:

    alias d="docker-compose exec"
    alias dfab="d web fab"
    alias dyarn="d web yarn"

Or:

    alias d="docker-compose exec web"
    
And then:

    $ d fab 
    $ d yarn serve
   
   
***Tip***- If `docker-compose up -d` takes too long to run, you might consider the following:
    
    $ cp docker-compose.override.yml.example docker-compose.override.yml

This override file will point the `elasticsearch` service to a `hello-world` image instead of its real settings.
Use this [override file](https://docs.docker.com/compose/extends/#multiple-compose-files) to override more settings for your own development environment.  

## Administering and Developing Capstone <a id="administering-and-developing-capstone"></a>
- [Testing](#testing)
- [Requirements](#requirements)
- [Applying model changes](#applying-model-changes)
- [Stored Postgres functions](#stored-postgres-functions)
- [Running Command Line Scripts](#running-command-line-scripts)
- [Local debugging tools](#local-debugging-tools)
- [Download real data locally](#download-real-data-locally )
- [Model versioning](#model-versioning)

### Testing <a id="testing"></a>

We use pytest for tests. Some notable flags:

Run all tests:

    (capstone)$ pytest

Run one test:

    (capstone)$ pytest -k test_name

Run tests without capturing stdout, to allow debugging with pdb:

    (capstone)$ pytest -s

Run tests in parallel for speed:

    (capstone)$ pytest -n <number of processes>

### Requirements <a id="requirements"></a>

Top-level requirements are stored in `requirements.in`. After updating that file, you should run

    (capstone)$ fab pip-compile

to freeze all subdependencies into `requirements.txt`.

To ensure that your environment matches `requirements.txt`, you can run

    (capstone)$ pip-sync

This will add any missing packages and remove any extra ones.

### Applying model changes <a id="applying-model-changes"></a>

Use Django to apply migrations. After you change `models.py`:

    (capstone)$ ./manage.py makemigrations

This will write a migration script to `cap/migrations`. Then apply:

    (capstone)$ fab migrate

### Stored Postgres functions <a id="stored-postgres-functions"></a>

Some Capstone features depend on stored functions that allow Postgres to deal with XML and JSON fields.
See `set_up_postgres.py` for documentation.

### Running Command Line Scripts <a id="running-command-line-scripts"></a>

Command line scripts are defined in `fabfile.py`. You can list all available commands using `fab -l`, and run a
command with `fab command_name`.

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

Installing the temporal_tables extension is recommended for performance. If not installed, a pure postgres version
will be installed by set_up_postgres.py; this is handy for development.

### Download real data locally <a id="download-real-data-locally"></a>
*These instructions are likely only going to be useful for internal users with access to our production databases and data stores, but there's no reason you couldn't set up an s3 bucket with the expected structure to ingest volumes. If you have any interest in working on something that requires this, file an issue to request that we extend the documentation. We've found very few instances where our test cases did not fully meet our dev needs.*

To write test data and fixtures for given volume and case:
run the fab command `fab add_test_case` with a volume barcode
(like `fab add_test_case:32044057891608_0001`)
- You will need to point STORAGES['ingest_storage'] to real harvard-ftl-shared

### Working with javascript <a id="working-with-javascript"></a>

We use [Vue CLI 3](https://cli.vuejs.org/) to compile javascript files, so you can use modern javascript and it will be
transpiled to support the browsers listed in package.json. New javascript entrypoints can be added to vue.config.js and
included in templates with `{% render_bundle %}`.

If you want to edit javascript files, you will need to install `node` and the package.json javascript packages:

    $ brew install node
    $ npm install -g yarn
    $ yarn install --frozen-lockfile

You can then run the local javascript development server in a separate terminal window, or in the background:

    $ yarn serve

This will cause javascript files to be loaded live from http://127.0.0.1:8080/ and recompiled on save in the background.
Your changes should be present at http://127.0.0.1:8000.

*Important:* Any time you run `yarn serve`, before committing, you must then run

    $ yarn build

to compile the production assets and recreate webpack-stats.json, or else tests will fail when you send a pull request.
(If you don't change anything, you could also just undo the changes to webpack-stats.json.)

Installing node and running `yarn serve` is not necessary unless you are editing javascript. On a clean checkout, or
after shutting down `yarn serve` and running `yarn build`, the local dev server will use the compiled production
assets. Under the hood, use of the local dev server vs. production assets is controlled by the contents of
`webpack-stats.json`.

*Installing packages*: You can install new packages with:

    $ yarn add --dev package

After changing package.json or yarn.lock, you should run `fab update_docker_image_version` to ensure that docker users
get the updates.

*Yarn and docker:* `yarn` will also work inside docker-compose:

    $ docker-compose run web yarn build

`yarn` packages inside docker are stored in `/node_modules`. The `/app/capstone/node_modules` folder is just an empty
mount to block out any `node_modules` folder that might exist on the host.

### Elasticsearch <a id="elasticsearch"></a>

For local dev, Elasticsearch will automatically be started by `docker-compose up -d`. You can then run
`fab refresh_case_body_cache` to populate CaseBodyCache for all cases, and `fab rebuild_search_index` to populate the
search index.

For debugging, see settings.py.example for an example of how to log all requests to and from Elasticsearch.

It may also be useful to run Kibana to directly query Elasticsearch from a browser GUI:

    $ brew install kibana
    $ kibana -e http://127.0.0.1:9200

You can then go to Kibana -> Dev Tools to run any of the logged queries, or `GET /_mapping` to see the search indexes.

## Documentation <a id="documentation"></a>
This readme, code comments, and the API usage docs are the only docs we have. If you want something documented more thoroughly, file an issue and we'll get back to you.

## Examples <a id="examples"></a>
See the [CAP examples repo](https://github.com/harvard-lil/cap-examples) for some ideas about getting started with this data.
