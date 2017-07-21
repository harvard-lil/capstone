# CAP API - developer notes
## Instructions to start up Postgres

Make sure postgres is installed.
Please see [Postgresql docs] (https://www.postgresql.org/download/) for details.

In terminal:
```
  createdb cap
  psql
  CREATE ROLE capuser WITH LOGIN PASSWORD 'cap';
  GRANT ALL PRIVILEGES ON DATABASE cap TO capuser;
  ALTER USER capuser WITH PASSWORD 'cap';
  ALTER USER capuser CREATEDB;
  ALTER ROLE capuser SET client_encoding TO 'utf8';
  ALTER ROLE capuser SET timezone TO 'UTC';
  \q
```

After quitting out of psql, log in again as `capuser`:

```
  psql -d cap -U capuser
```

If you are seeing this error:
`FATAL: Peer authentication failed for user "postgres"`

```
  SHOW hba_file;
```
Find hba_file and edit the following line (could be multiple lines!):
```
local   all             postgres                                peer
```
change to:
```
local   all             postgres                                md5
```
See [here] (https://stackoverflow.com/questions/18664074/getting-error-peer-authentication-failed-for-user-postgres-when-trying-to-ge) for an explanation.

You should be all set!


For testing:
```
  psql
  GRANT ALL PRIVILEGES ON DATABASE test_cap TO capuser;
  ALTER DATABASE test_cap OWNER TO capuser;
  \q
```

```
python manage.py test capapi.tests
```
