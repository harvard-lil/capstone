from helpers import pg_connect
from models import Base

def create_tables(pg_engine):
    Base.metadata.create_all(pg_engine)

if __name__ == "__main__":
    pg_engine = pg_connect()
    create_tables(pg_engine)
