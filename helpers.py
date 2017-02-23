import configparser
import sqlalchemy
from sqlalchemy.pool import NullPool


def get_pg_config():
    """
        Load postgres config variables from an environment file.
    """
    config = configparser.ConfigParser()
    config.read('/ftldata/misc/pg.capstone.cnf')
    return config['db']

def get_pg_url():
    """
        Format postgres config variables into a connection string.
    """
    config = get_pg_config()
    return 'postgresql://%s:%s@%s/%s' % (
        config['user'], config['password'], config['host'], config['dbname'],
    )

def pg_connect():
    """
        Set up a connection to postgres.

        NOTE: The poolclass=NullPool business is convenient for connections in ingest_files.py,
        where each connection is being used once in its own process and thrown away. It's probably a bad idea in general.
    """
    return sqlalchemy.create_engine(get_pg_url(), client_encoding='utf8', poolclass=NullPool)

def sql_debug():
    """
        Handy function to cause sqlalchemy to print all SQL it runs.
    """
    import logging
    logging.basicConfig()
    logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)


# This was an experiment in using the experimental asyncpg library supported in Python 3.5+.
# Keeping it around in case it's useful.
# For now, I found that trying to use asyncpg required much lower-level code, because asyncpgsa doesn't support
# sqlalchemy-ORM yet, and it also required keeping track of whether each function was async or not in a way that
# wasn't very ergonomic.

# from asyncpgsa import pg
# async def connect_async():
#     config = get_pg_config()
#     return await pg.init(
#         host=config['host'],
#         database=config['dbname'],
#         user=config['user'],
#         password=config['password'],
#         min_size=5,
#         max_size=10
#     )
# do cool async stuff:
# import asyncio
# async def main():
#     sync_con, async_con = await connect()
#
# if __name__ == '__main__':
#     loop = asyncio.get_event_loop()
#     loop.run_until_complete(main())