FROM postgres:9.6

RUN apt-get update && \
    apt-get install -y libpq-dev && \
    apt-get install -y postgresql-9.6-plv8

# One could add temporal_tables installation here,
# if one could get it working.... non-trivial

# set up rum
RUN apt-get update && \
    apt-get install -y build-essential && \
    apt-get install -y systemtap-sdt-dev && \
    apt-get install -y postgresql-server-dev-9.6 && \
    apt-get install -y pgxnclient && \
    USE_PGXS=1 pgxn install rum
