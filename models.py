
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table
from sqlalchemy.sql.type_api import UserDefinedType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship


### custom column types ###

class XMLType(UserDefinedType):
    """ Column type for Postgres XML columns. """
    def get_col_spec(self):
        return 'XML'



Base = declarative_base()

### join tables ###

case_pages = Table('cap_case_page', Base.metadata,
    Column('case_id', ForeignKey('cap_case.id'), primary_key=True),
    Column('page_id', ForeignKey('cap_page.id'), primary_key=True)
)

### models ###

class Volume(Base):
    __tablename__ = 'cap_volume'
    id = Column(Integer, primary_key=True)
    barcode = Column(String, unique=True, index=True)
    orig_xml = Column(XMLType)

    cases = relationship("Case", back_populates="volume")
    pages = relationship("Page", back_populates="volume")

class Case(Base):
    __tablename__ = 'cap_case'
    id = Column(Integer, primary_key=True)
    barcode = Column(String, unique=True, index=True)
    orig_xml = Column(XMLType)

    volume_id = Column(Integer, ForeignKey('cap_volume.id'), index=True)
    volume = relationship("Volume", back_populates="cases")

    pages = relationship('Page', secondary=case_pages, back_populates='cases')

class Page(Base):
    __tablename__ = 'cap_page'
    id = Column(Integer, primary_key=True)
    barcode = Column(String, unique=True, index=True)
    orig_xml = Column(XMLType)

    volume_id = Column(Integer, ForeignKey('cap_volume.id'), index=True)
    volume = relationship("Volume", back_populates="pages")

    cases = relationship('Case', secondary=case_pages, back_populates='pages')