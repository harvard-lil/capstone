FROM registry.lil.tools/library/postgres:11.10

RUN apt-get update && \
    apt-get install -y libpq-dev

# install temporal_tables
RUN apt-get update && \
    apt-get install -y build-essential && \
    apt-get install -y systemtap-sdt-dev && \
    apt-get install -y postgresql-server-dev-11 && \
    apt-get install -y git && \
    git clone https://github.com/mlt/temporal_tables.git && \
    cd temporal_tables && \
    git checkout 6cc86eb03d618d6b9fc09ae523f1a1e5228d22b5 && \
    make && \
    make install
