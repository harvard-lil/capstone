# INSTRUCTIONS TO START UP POSTGRES
# make sure postgers is loaded.
# in terminal
  $ createdb cap
  $ psql
  $ CREATE ROLE capuser WITH LOGIN PASSWORD 'cap';
  $ GRANT ALL PRIVILEGES ON DATABASE cap TO cap;
  $ ALTER USER capuser WITH PASSWORD 'cap';
  $ ALTER USER capuser CREATEDB;
  $ ALTER ROLE capuser SET client_encoding TO 'utf8';
  $ ALTER ROLE capuser SET timezone TO 'UTC';
  $ SHOW hba_file;
# and then follow these directions
  https://stackoverflow.com/questions/18664074/getting-error-peer-authentication-failed-for-user-postgres-when-trying-to-ge

  $ \q
