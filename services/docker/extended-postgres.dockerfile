FROM postgres:9.6

RUN apt-get update && \
    apt-get install -y libpq-dev && \
    apt-get install -y postgresql-9.6-plv8

# One could add temporal_tables installation here,
# if one could get it working.... non-trivial
