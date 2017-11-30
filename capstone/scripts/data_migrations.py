import datetime
import re
import traceback
from collections import defaultdict
from contextlib import contextmanager

import xmltodict
from django.db import transaction
from lxml import etree

from capdb.models import VolumeXML, PageXML, CaseXML, DataMigration
from .helpers import nsmap, parse_xml

def run_pending_migrations():
    """ 
        This will execute all pending data migrations in one transaction. 
        the session scope function comes from helpers, and uses contextmanager
    """
    for migration in DataMigration.objects.filter(status="pending"):
        with migration_session_scope(migration):
            migration.transaction_timestamp=datetime.datetime.now()
            migration.status = "applied"
            if migration.case_xml_changed is not None:
                for case in migration.case_xml_changed:
                    migration.case_xml_rollback = modify(case, 'case')
            if migration.alto_xml_changed is not None:
                for alto in migration.alto_xml_changed:
                    migration.case_xml_rollback = modify(alto, 'alto')
            if migration.volume_xml_changed is not None:
                for volume in migration.volume_xml_changed:
                    migration.case_xml_rollback = modify(volume, 'volume')
            migration.save()

def run_migration(id):
    """ 
        Runs one migration, based on ID
    """
    migration = DataMigration.get(id=id)
    with migration_session_scope(migration):
        migration.transaction_timestamp=datetime.datetime.now()
        migration.status = "applied"
        if migration.case_xml_changed is not None:
            for case in migration.case_xml_changed:
                migration.case_xml_rollback = modify(case, 'case')
        if migration.alto_xml_changed is not None:
            for alto in migration.alto_xml_changed:
                migration.case_xml_rollback = modify(alto, 'alto')
        if migration.volume_xml_changed is not None:
            for volume in migration.volume_xml_changed:
                migration.case_xml_rollback = modify(volume, 'volume')
        migration.save()


def modify(changes, type):
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
              "parent_xpath": "(if creating)",
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
            "parent_xpath": "(if creating)",
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
              "parent_xpath": "(if creating)",
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
        doc = VolumeXML.objects.get(barcode=changes['barcode'])
    elif type == 'case':
        doc = CaseXML.objects.get(barcode=changes['case_id'])
    elif type == 'alto':
        doc = PageXML.objects.get(barcode=changes['alto_id'])

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
            # TODO: FIXME
            # print("Provided xpath must select ONE element. {} elements selected with {} in {}".format(len(elements), xpath, case_changes['case_id']))
            return False

        element_list[index] = elements[0]

    rollback_list = defaultdict()
    #This loops through the changes and makes an array of elements to modify
    for index, change in enumerate(changes['changes']):
        element = element_list[index]

        rollback_list_entry = {}

        rollback_list_entry['complete_element'] = xmltodict.parse(etree.tostring(element))
        rollback_list_entry['actions'] = {}
        if 'type' in change:
            rollback_list_entry['type'] = change['type']

        if 'remove' in change['actions']:
            if change['actions']['remove'] is True:
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
    doc.save()

    return rollback_list

def normalize_namespace(xpath):
    for short in nsmap:
        xpath = xpath.replace('{'+ nsmap[short] +'}', short + ':')
    return xpath

@contextmanager
def migration_session_scope(migration):
    """Creates the transactional scope around the migration"""
    try:
        with transaction.atomic():
            yield
    except Exception as err:
        tb = traceback.format_exc(limit=2)
        error_migration(migration, err, tb)
        raise

def error_migration(migration, err, tb):
    """
        This sets the status of a migration to "err" and captures the 
        traceback
    """
    migration.status = "error"
    migration.traceback = "{}\n{}".format(err, tb)
    migration.transaction_timestamp = datetime.datetime.now()
    migration.save()


def generate_migration_from_case(orig_case, updated_case):

    """ This compares two cases and makes a data migration JSON based on them"""
    parsed_orig_case = parse_xml(orig_case.orig_xml)
    updated_tree = updated_case.root
    original_tree = parsed_orig_case.root

    #set up the basic structure of the change set map
    modified = {}
    modified['case'] = {}
    modified['case']['barcode'] = orig_case.case_id.split("_")[0]
    modified['case']['case_id'] = orig_case.case_id
    modified['case']['changes']= []
    modified['alto'] = defaultdict(list)

    alto_files = {}
    for alto in orig_case.pages.all():
        alto_fileid = "_".join((["alto"] + alto.barcode.split('_')[1:3]))
        alto_files[alto_fileid] = alto 

    original_element_dict = _get_element_dict(original_tree)
    updated_element_dict = _get_element_dict(updated_tree)

    deleted_xpaths = set(original_element_dict) -  set(updated_element_dict)
    added_xpaths = set(updated_element_dict) -  set(original_element_dict)

    elements_to_delete_from_tree = []
    for xpath in deleted_xpaths:
        element = original_tree.find(xpath)
        if _in_casebody(element):
            for alto_page in _get_alto_elements(element, parsed_orig_case, alto_files):
                modified['alto'][alto_page['barcode']].append(
                    _delete_alto_element('layout', element.get('id'))
                )
            modified['case']['changes'].append(_delete_casebody_element(element.get('id')))
        else:
            modified['case']['changes'].append(_delete_case_element(xpath, element))
        elements_to_delete_from_tree.append(element)

    elements_to_add_to_tree = []
    for xpath in added_xpaths:
        element = updated_tree.find(xpath)
        if _in_casebody(element):
            for alto_page in _get_alto_elements(element, parsed_orig_case, alto_files):
                modified['alto'][alto_page['barcode']].append(
                    _delete_alto_element('layout', element.get('id'))
                )

            modified['case']['changes'].append(_add_casebody_element(element.get('id'), updated_tree.getpath(element.getparent().get('id')), element.items(), element.tag, element.text))
        else:
            modified['case']['changes'].append(_add_case_element(xpath, updated_tree.getpath(element.getparent()), element.items(), element.tag, element.text))
        elements_to_add_to_tree.append(element)
    

    for element in elements_to_add_to_tree:
        element.getparent().remove(element)

    for element in elements_to_delete_from_tree:
        element.getparent().remove(element)

    # now that we've checked for additions and deletions, check for changes with matching paths
    for original_element in original_tree.iter():
        readable_xpath = original_tree.getelementpath(original_element)
        xpath = original_tree.getpath(original_element)
        updated_element_search = updated_tree.xpath(xpath)

        updated_element = updated_element_search[0]


        if original_element.tag != updated_element.tag:
            if _in_casebody(original_element):
                for alto_page in _get_alto_elements(element, parsed_orig_case, alto_files):
                    if alto_page['structure_tag'] is not None:
                        modified['alto'][alto_page['barcode']].append(
                            _change_alto_attrib(original_element.get('id'), "LABEL", updated_element.tag)
                        )
                modified['case']['changes'].append(_change_casebody_tag(original_element.get('id'), updated_element.tag))
            else:
                modified['case']['changes'].append(_change_case_tag(xpath, readable_xpath, updated_element.tag))
        
        # check for modified element text
        if original_element.text != updated_element.text:
            if _in_casebody(original_element):
                if len(updated_element.text.split(" ")) != len(original_element.text.split(" ")):
                    return {"error": "adding or removing words from case text is not yet implemented"}
                wordcount = 0
                for alto_page in _get_alto_elements(original_element, parsed_orig_case, alto_files):
                    words = alto_page['textblock']("alto|String")
                    for word in words:
                        if updated_element.text.split(" ")[wordcount] != original_element.text.split(" ")[wordcount]:
                            # update ALTO & set the character confidence and word confidence to 100%
                            modified['alto'][alto_page['barcode']].append(
                                _change_alto_attrib(original_element.get('id'), "WC", "1.00")
                            )
                            modified['alto'][alto_page['barcode']].append(
                                _change_alto_attrib(original_element.get('id'), "CC", '0' * len(updated_element.text.split(" ")[wordcount]))
                            )
                            modified['alto'][alto_page['barcode']].append(
                                _change_alto_attrib(original_element.get('id'), "CONTENT", updated_element.text.split(" ")[wordcount])
                            )
                        wordcount += 1
                modified['case']['changes'].append(_change_casebody_content(original_element.get('id'), updated_element.text))
            else:
                modified['case']['changes'].append(_change_case_content(xpath, readable_xpath, updated_element.text))

        # I don't think the stuff below should directly affect the ALTO

        # check if any attributes were added or removed
        if set(original_element.keys()) != set(updated_element.keys()):
            deleted_attributes = set(original_element.keys()) - set(updated_element.keys())
            added_attributes = set(updated_element.keys()) - set(original_element.keys())
            for attribute in deleted_attributes:
                if _in_casebody(original_element):
                    modified['case']['changes'].append(_delete_casebody_attrib(original_element.get('id'), attribute))
                else:
                    modified['case']['changes'].append(_delete_case_attrib(xpath, readable_xpath, attribute))
            for attribute in added_attributes:
                if _in_casebody(original_element):
                    modified['case']['changes'].append(_change_casebody_attrib(original_element.get('id'), attribute))
                else:
                    modified['case']['changes'].append(_change_case_attrib(xpath, readable_xpath, attribute, updated_element.get(attribute)))
                    
        # check to see if any attribute values changed
        for attribute in original_element.keys():
            if original_element.get(attribute) != updated_element.get(attribute):
                if _in_casebody(original_element):
                    modified['case']['changes'].append(_change_casebody_attrib(original_element.get('id'), attribute))
                else:
                    modified['case']['changes'].append(_change_case_attrib(xpath, readable_xpath, attribute, updated_element.get(attribute)))
    

    alto_migrations= []
    for alto in modified['alto']:
        alto_migrations.append({
            "barcode": alto.split("_")[0],
            "alto_id": alto,
            "changes": modified['alto'][alto]
        })

    migration = {}
    migration['notes'] = "Automatically generated during a CaseXML modification using the update_case_alto_unified function in capdb/utils.py"
    migration['status'] = "ephemeral"
    migration['author'] = "update_case_alto_unified"
    migration['initiator'] = "update_case_alto_unified"
    migration['case_xml_changed'] = [modified['case']]
    migration['alto_xml_changed'] = alto_migrations

    return {"ok": migration}


def _in_casebody(element):
    return element.tag.startswith("{" + nsmap['casebody']) and not element.tag.endswith('casebody')

def _get_element_pages(element):
    element_pages = {}
    if "pgmap" in element.keys() and ' ' in element.get("pgmap"):
        element_pages = { page.split('(')[0]: page.split('(')[1][:-1] for page in element.get("pgmap").split(" ") }
    elif "pgmap" in element.keys():
        element_pages = { element.get("pgmap"): len(element.text.split(" ")) }
    return element_pages

def _get_alto_connections(parsed_case, element):
    alto_connections = {}
    #this might be sketchy if it turns out that the case reference isn't always first
    alto_element_references = parsed_case('mets|area[BEGIN="{}"]'.format(element.get('id'))).parent().nextAll('mets|fptr')
    for area in alto_element_references('mets|area'):
        pgmap = area.get('BEGIN').split(".")[0].split("_")[1]
        alto_connections[pgmap] = (area.get('FILEID'), area.get('BEGIN'))
    return alto_connections

def _get_element_dict(tree):
    return_dict = {}
    for element in tree.iter():
        return_dict[tree.getelementpath(element)] = {}
        return_dict[tree.getelementpath(element)]['attributes'] = {attrib: element.get(attrib) for attrib in element.keys()}
        return_dict[tree.getelementpath(element)]['content'] = element.text
        if element.getnext() is not None:
            return_dict[tree.getelementpath(element)]['next'] = tree.getelementpath(element.getnext())
        else:
            return_dict[tree.getelementpath(element)]['next'] = None
        if element.getparent() is not None:
            return_dict[tree.getelementpath(element)]['parent'] = tree.getelementpath(element.getparent())
        else:
            return_dict[tree.getelementpath(element)]['parent'] = None
        if element.get('id') is not None:
            return_dict[tree.getelementpath(element)]['id'] = element.get('id')
        else:
            return_dict[tree.getelementpath(element)]['id'] = None
    return return_dict

def _get_alto_elements(element, parsed_case, alto_files):
    element_pages = _get_element_pages(element)
    alto_connections = _get_alto_connections(parsed_case, element)
    for page in element_pages:
        return_map = {}
        alto_file = alto_files[alto_connections[page][0]]
        parsed_alto_file = parse_xml(alto_file.orig_xml)
        return_map['barcode'] = alto_files[alto_connections[page][0]].barcode
        return_map['page'] = alto_connections[page][0]
        return_map['textblock'] = parsed_alto_file('alto|TextBlock[TAGREFS="{}"]'.format(element.get('id')))
        return_map['structure_tag'] = parsed_alto_file('alto|StructureTag[ID="{}"]'.format(element.get('id')))
        yield return_map

def _change_case_content(xpath, readable_xpath, content):
    return  { "type": "non_casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "content": content }}
def _change_casebody_content(element_id, content):
    return  { "type": "casebody", "element_id": element_id, "actions": { "content": content }}
def _change_case_attrib(xpath, readable_xpath, attrib, value):
    return { "type": "casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "attributes": { "add_update": { attrib: value }}}}
def _change_casebody_attrib(element, attrib, value):
    return { "type": "casebody", "element_id": element, "actions": { "attributes": { "add_update": { attrib: value }}}}
def _delete_case_attrib(xpath, readable_xpath, attrib):
    return { "type": "casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "attributes": { "delete": [ attrib ]}}}
def _delete_casebody_attrib(element, attrib, value):
    return { "type": "casebody", "element_id": element, "actions": { "attributes": { "delete": [ attrib ]}}}
def _change_case_tag(xpath, readable_xpath, tag):
    return  { "type": "casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "name": tag }}
def _change_casebody_tag(element_id, tag):
    return  { "type": "casebody", "element_id": element_id, "actions": { "name": tag }}
def _delete_case_element(xpath, readable_xpath):
    return  { "type": "non_casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "remove": True }}
def _add_case_element(xpath, parent, attribute_dict, name, content):
    return  { "type": "non_casebody", "xpath": xpath, "content": content, "name": name, "parent_xpath": parent, "actions": { "create": True, "attributes": { "add_update": { attribute_dict } } } }
def _add_casebody_element(element_id, parent, attribute_dict, name, content):
    return  { "type": "casebody", "content": content, "name": name, "element_id": element_id, "parent_element_id": parent, "actions": { "create": True, "attributes": { "add_update": { attribute_dict } } } }
def _delete_casebody_element(element_id):
    return  { "type": "casebody", "element_id": element_id, "actions": { "remove": True }}
def _change_alto_attrib(element, attrib, value):
    return { "type": "layout", "element": element, "actions": { "add_update": { attrib: value }}}
def _delete_alto_element(element_type, element_id):
    return { "type": element_type, "element_id": element_id, "actions": { "remove": True }}