
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Table
from sqlalchemy import DateTime
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.sql.type_api import UserDefinedType
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

from versioning import Versioned


### custom column types ###


class XMLType(UserDefinedType):
    """ Column type for Postgres XML columns. """
    def get_col_spec(self):
        return 'XML'



class Base(Versioned):
    pass
Base = declarative_base(cls=Base)

### join tables ###

# case_pages = Table('cap_case_page', Base.metadata,
#     Column('case_id', ForeignKey('cap_case.id'), primary_key=True),
#     Column('page_id', ForeignKey('cap_page.id'), primary_key=True)
# )

### models ###

class Volume(Base):
    __tablename__ = 'cap_volume'
    id = Column(Integer, primary_key=True)
    barcode = Column(String, unique=True, index=True)
    orig_xml = Column(XMLType)

    # cases = relationship("Case", back_populates="volume")
    # pages = relationship("Page", back_populates="volume")

class Case(Base):
    __tablename__ = 'cap_case'
    id = Column(Integer, primary_key=True)
    barcode = Column(String, unique=True, index=True)
    orig_xml = Column(XMLType)

    volume_id = Column(Integer, ForeignKey('cap_volume.id'), index=True)
    volume = relationship("Volume", backref="cases")

    # pages = relationship('Page', secondary=case_pages, back_populates='cases')
    pages = association_proxy("case_pages", "page")

class Page(Base):
    __tablename__ = 'cap_page'
    id = Column(Integer, primary_key=True)
    barcode = Column(String, unique=True, index=True)
    orig_xml = Column(XMLType)

    volume_id = Column(Integer, ForeignKey('cap_volume.id'), index=True)
    volume = relationship("Volume", backref="pages")

    # cases = relationship('Case',
    #                      secondary="join(B, D, B.d_id == D.id)."
    #                         "join(C, C.d_id == D.id)",
    #                      backref='pages')
    cases = association_proxy("case_pages", "case")

class CasePage(Base):
    __tablename__ = 'cap_case_page'
    case_id = Column(Integer, ForeignKey('cap_case.id'), primary_key=True)
    page_id = Column(Integer, ForeignKey('cap_page.id'), primary_key=True)
    case = relationship("Case", backref="case_pages")
    page = relationship("Page", backref="case_pages")

class Changeset(Base):
    transaction_timestamp = Column(DateTime)
    message = Column(Text)