from helpers import pg_connect
from sqlalchemy.orm import sessionmaker
from sqlalchemy import *
from models import Volume, Page, Case, CasePage, DataMigration
from pprint import pprint
import json
from lxml import etree
from io import StringIO, BytesIO
from contextlib import contextmanager
import re 
import xmltodict
from collections import defaultdict
import datetime

nsmap={'mets': 'http://www.loc.gov/METS/', 'case': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case:v1', 'casebody': 'http://nrs.harvard.edu/urn-3:HLS.Libr.US_Case_Law.Schema.Case_Body:v1', 'info': 'info:lc/xmlns/premis-v2', 'alto': "http://www.loc.gov/standards/alto/ns-v3#" }

def run_pending_migrations():
    """ 
        This will execute all pending data migrations in one transaction. 
        the session scope function comes from helpers, and uses contextmanager
    """
    for migration in get_migrations('pen'):
        with migration_session_scope(migration.id) as session:
            migration.transaction_timestamp=datetime.datetime.now()
            migration.status="app"
            if migration.case_xml_changed is not None:
                for case in migration.case_xml_changed:
                    migration.case_xml_rollback = modify(session, case, 'case')
            if migration.alto_xml_changed is not None:
                for alto in migration.alto_xml_changed:
                    migration.case_xml_rollback = modify(session, alto, 'alto')
            if migration.volume_xml_changed is not None:
                for volume in migration.volume_xml_changed:
                    migration.case_xml_rollback = modify(session, volume, 'volume')

def get_migrations(status=None):
    """ 
        Argument: status (str)
        Yields: DB row

        This generator will retrieve all data migrations, possibly filtered
        by a specified status, which is its lone argument
    """
    pg_con = pg_connect()
    Session = sessionmaker(bind=pg_con)
    session = Session()

    if status is not None:
        dMigrations = session.query(DataMigration).filter_by(status=status)  
    else:
        dMigrations = session.query(DataMigration)  

    for migration in dMigrations:
        yield migration


def modify(session, changes, type):

    """
        This function will take a set of changes to be applied to a document,
        apply the changes, and return a set of rollback instructions to be stored
        in the migration database entry.

        Right now, the following formats are assumed with this function:

        Volumes:
        [
          {
            "barcode": "32044123321123",
            "changes": [{
              "xpath": "(if non_casebody) //mets/blah/blah[@BLAH=666]/p[2]",
              "actions": {
                "remove": false,
                "create": false,
                "content": "love them new words",
                "name": "judge",
                "attributes": {
                  "delete": ["name", "name", "name"],
                  "add_update": {
                    "id": "some identifier",
                    "alt_id": "some other identifier"
                  }
                }
              }
            }]
          }
        ]


        Cases:
        [{
          "barcode": "32044123321123",
          "case_id": "32044123321123_002",
          "changes": [{
            "type": "non_casebody/casebody",
            "element_id": "(if casebody) b-123a",
            "xpath": "(if non_casebody) //mets/blah/blah[@BLAH=666]/p[2]",
            "actions": {
              "remove": false,
              "create": false,
              "content": "love them new words",
              "name": "judge",
              "attributes": {
                "delete": ["name", "name", "name"],
                "add_update": {
                  "id": "some identifier",
                  "alt_id": "some other identifier"
                }
              }
            }
          }]
        }]


        Altos:
        [{
          "barcode": "32044123321123",
          "alto_id": "32044123321123_002",
          "changes": [{
              "type": "tag/layout/other",
              "element_id": "(if tag or layout) b-123a",
              "xpath": "(if other) //mets/blah/blah[@BLAH=666]/p[2]",
              "actions": {
                "remove": false,
                "create": false,
                "content": "love them new words",
                "name": "judge",
                "attributes": {
                  "delete": ["name", "name", "name"],
                  "add_update": {
                    "id": "some identifier",
                    "alt_id": "some other identifier"
                  }
                }
              }
            }
          ]
        }]
    """
    if type == 'volume':
        doc = session.query(Volume).filter_by(barcode=changes['barcode']).first()
    elif type == 'case':
        doc = session.query(Case).filter_by(barcode=changes['case_id']).first()
    elif type == 'alto':
        doc = session.query(Page).filter_by(barcode=changes['alto_id']).first()

    root = etree.fromstring(doc.orig_xml)
    tree = etree.ElementTree(root)

    element_list = defaultdict()
    for index, change in enumerate(changes['changes']):
        if 'element_id' in change:
            elements = tree.findall(".//*[@id='{}']".format(change['element_id']), namespaces=nsmap)
            if len(elements) != 1:
                elements = tree.findall(".//*[@ID='{}']".format(change['element_id']), namespaces=nsmap)
        elif 'xpath' in change:
            elements = tree.xpath(change['xpath'], namespaces=nsmap)

        if len(elements) != 1:
            print("Provided xpath must select ONE element. {} elements selected with {} in {}".format(len(elements), xpath, case_changes['case_id']))
            return False

        element_list[index] = elements[0]

    rollback_list = defaultdict()
    rollback = defaultdict()
    #This loops through the changes and makes an array of elements to modify
    for index, change in enumerate(changes['changes']):
        element = element_list[index]

        rollback_list_entry = {}

        rollback_list_entry['complete_element'] = xmltodict.parse(etree.tostring(element))
        rollback_list_entry['actions'] = {}
        if 'type' in change:
            rollback_list_entry['type'] = change['type']

        if 'remove' in change['actions']:
            if change['actions']['remove'] == True:
                rollback_list_entry['actions']['create'] = True
                rollback_list_entry['parent_path'] = element.getparent()
                rollback_list_entry['parent_index'] = element.getparent().index(element)
                rollback_list.append(rollback_list_entry)
                element.getparent().remove(element)
                continue

        if 'name' in change['actions']:
            tag_breakdown = re.match('({[^}]+})(.*)', element.tag)
            namespace = tag_breakdown.group(1)
            name = tag_breakdown.group(2)
            if namespace is not None:
                element.tag = "{}{}".format(namespace, change['actions']['name'])
            else:
                element.tag = change['actions']['name']
            rollback_list_entry['actions']['name'] = name

        if 'content' in change['actions']:
            rollback_list_entry['actions']['content'] = element.text
            element.text = change['actions']['content']

        if 'attributes' in change['actions']:
            rollback_list_entry['actions']['attributes'] = {}
            if 'remove' in change['actions']['attributes']:
                rollback_list_entry['actions']['attributes']['add_update'] = {}
                for attribute in change['actions']['attributes']['remove']:
                    #yes, I do want the whole thing to die if this fails
                    rollback_list_entry['actions']['attributes']['add_update'][attribute] = element.attrib[attribute]
                    del element.attrib[attribute]
            if 'add_update' in change['actions']['attributes']:
                for attribute in change['actions']['attributes']['add_update']:

                    if attribute in element.attrib:
                        if 'add_update' not in rollback_list_entry['actions']['attributes']:
                            rollback_list_entry['actions']['attributes']['add_update'] = {}
                        rollback_list_entry['actions']['attributes']['add_update'][attribute] = element.attrib[attribute]
                    else:
                        if 'remove' not in rollback_list_entry['actions']['attributes']:
                            rollback_list_entry['actions']['attributes']['remove'] = []
                        rollback_list_entry['actions']['attributes']['remove'].append(attribute)

                    element.attrib[attribute] = change['actions']['attributes']['add_update'][attribute]

        rollback_list[index] = rollback_list_entry


    for index, change in enumerate(changes['changes']):
        element = element_list[index]
        rollback = rollback_list[index]

        if 'element_id' in change:
            for o_tag in rollback['complete_element']:
                if '@ID' in rollback['complete_element'][o_tag]:
                    rollback['element_id'] = element.attrib['ID']
                if '@id' in rollback['complete_element'][o_tag]:
                    rollback['element_id'] = element.attrib['id']
        elif 'xpath' in change:
            rollback['xpath'] = normalize_namespace(tree.getelementpath(element))
        
        rollback['numeric_xpath'] = tree.getpath(element)

        if 'remove' not in change['actions']:
            del rollback['complete_element']
    
    doc.orig_xml = etree.tostring(root, pretty_print=True).decode("utf-8")

    return rollback_list

def normalize_namespace(xpath):
    for short in nsmap:
        xpath = xpath.replace('{'+ nsmap[short] +'}', short + ':')
    return xpath

@contextmanager
def migration_session_scope(migration_id):
    """Creates the transactional scope around the migration"""
    pg_con = pg_connect()
    Session = sessionmaker(bind=pg_con)
    session = Session()
    try:
        yield session
        session.commit()
    except Exception as err:
        session.rollback()

        import sys, traceback
        exc_type, exc_value, exc_traceback = sys.exc_info()
        tb = traceback.format_exc(limit=2)
        error_migration(migration_id, err, tb)

        raise
    finally:
        session.close()

def error_migration(migration_id, err, tb):
    """
        This sets the status of a migration to "err" and captures the 
        traceback
    """
    pg_con = pg_connect()
    Session = sessionmaker(bind=pg_con)
    session = Session()

    migration = session.query(DataMigration).get(migration_id)
    migration.status="err"
    migration.warn_except="{}\n{}".format(err, tb)
    migration.transaction_timestamp=datetime.datetime.now()

    session.commit()
    session.close()


if __name__ == '__main__':
    run_pending_migrations()
