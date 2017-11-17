from django.template.defaultfilters import slugify
from scripts.helpers import parse_xml, nsmap
from collections import defaultdict

import json

def generate_unique_slug(instance, raw_string, field='slug', max_tries=1000):
    """
        Get a unique slug for instance by sluggifying raw_string, checking database, and appending -1, -2 etc. if necessary.
        When checking uniqueness, ignore this object itself if it already exists in the database.

        Usage:
            my_instance.slug = generate_unique_slug(my_instance, 'Obj Title')
    """

    slug_base = "%s" % slugify(raw_string[:100])
    for count in range(max_tries):
        slug = slug_base
        if count:
            slug = "%s-%s" % (slug, count)

        # ORM query for objects of the same model, with the same slug
        found = type(instance).objects.filter(**{field: slug})

        # Exclude this exact instance from the query
        if instance.pk:
            found = found.exclude(pk=instance.pk)

        if not found.exists():
            return slug

    raise Exception("No unique slug found after %s tries." % max_tries)

def update_case_alto_unified(orig_case, updated_casebody):
    parsed_orig_case = parse_xml(orig_case.orig_xml)

    updated_tree = updated_casebody.root
    original_tree = parsed_orig_case.root
    modified = {}
    modified['case'] = {}
    modified['case']['barcode'] = orig_case.case_id.split("_")[0]
    modified['case']['case_id'] = orig_case.case_id
    modified['case']['changes']= []
    modified['alto'] = defaultdict(list)
    alto_files = {}

    # this is ugly, but I think it's the simplest way to organize this functionality
    def change_alto_attrib(element, attrib, value):
        return { "type": "layout", "element": element, "actions": { "add_update": { attrib: value }}}
    def change_case_content(xpath, readable_xpath, content):
        return  { "type": "non_casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "content": content }}
    def change_casebody_content(element_id, content):
        return  { "type": "casebody", "element_id": element_id, "actions": { "content": content }}
    def change_case_attrib(xpath, readable_xpath, attrib, value):
        return { "type": "casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "attributes": { "add_update": { attrib: value }}}}
    def change_casebody_attrib(element, attrib, value):
        return { "type": "casebody", "element_id": element, "actions": { "attributes": { "add_update": { attrib: value }}}}
    def delete_case_attrib(xpath, readable_xpath, attrib):
        return { "type": "casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "attributes": { "delete": [ attrib ]}}}
    def delete_casebody_attrib(element, attrib, value):
        return { "type": "casebody", "element_id": element, "actions": { "attributes": { "delete": [ attrib ]}}}
    def change_case_tag(xpath, readable_xpath, tag):
        return  { "type": "casebody", "xpath": xpath, "readable_xpath": readable_xpath, "actions": { "name": tag }}
    def change_casebody_tag(element_id, tag):
        return  { "type": "casebody", "element_id": element_id, "actions": { "name": tag }}

    for alto in orig_case.pages.all():
        alto_fileid = "_".join((["alto"] + alto.barcode.split('_')[1:3]))
        alto_files[alto_fileid] = alto

    for original_element in original_tree.iter():
        xpath = original_tree.getpath(original_element)
        readable_xpath = original_tree.getelementpath(original_element)
        updated_element_search = updated_tree.xpath(xpath)
        if len(updated_element_search) > 1:
            return {"error": "not tested with adding or removing elements yet"}
        updated_element = updated_element_search[0]
        in_casebody = False

        if original_element.tag.startswith("{" + nsmap['casebody']) and not original_element.tag.endswith('casebody'):
            in_casebody = True
            element_pages = {}
            alto_connections = {}
            if "pgmap" in original_element.keys() and ' ' in original_element.get("pgmap"):
                element_pages = { page.split('(')[0]: page.split('(')[1][:-1] for page in original_element.get("pgmap").split(" ") }
            elif "pgmap" in original_element.keys():
                element_pages = { original_element.get("pgmap"): len(original_element.text.split(" ")) }
            original_tree.getpath(original_tree.find("//casebody:casebody", nsmap))

            #this might be sketchy if it turns out that the case reference isn't always first
            alto_element_references = parsed_orig_case('mets|area[BEGIN="{}"]'.format(original_element.get('id'))).parent().nextAll('mets|fptr')
            for area in alto_element_references('mets|area'):
                pgmap = area.get('BEGIN').split(".")[0].split("_")[1]
                alto_connections[pgmap] = (area.get('FILEID'), area.get('BEGIN'))
        
        if original_element.tag != updated_element.tag:
            if in_casebody:
                for page in element_pages:
                    alto_file = alto_files[alto_connections[page][0]]
                    parsed_alto_file = parse_xml(alto_file.orig_xml)
                    structure_tag = parsed_alto_file('alto|StructureTag[ID="{}"]'.format(original_element.get('id')))
                    if structure_tag is not None:
                        structure_tag.attr.LABEL = updated_element.tag
                        
                        modified['alto'][alto_files[alto_connections[page][0]].barcode].append(
                            change_alto_attrib(original_element.get('id'), "LABEL", updated_element.tag)
                        )
                modified['case']['changes'].append(change_casebody_tag(original_element.get('id'), updated_element.tag))
            else:
                modified['case']['changes'].append(change_case_tag(xpath, readable_xpath, updated_element.tag))
        
        # check for modified element text
        if original_element.text != updated_element.text:
            if in_casebody:
                if len(updated_element.text.split(" ")) != len(original_element.text.split(" ")):
                    return {"error": "adding or removing words from case text is not yet implemented"}
                wordcount = 0
                for page in element_pages:
                    alto_file = alto_files[alto_connections[page][0]]
                    parsed_alto_file = parse_xml(alto_file.orig_xml)
                    textblock = parsed_alto_file('alto|TextBlock[TAGREFS="{}"]'.format(original_element.get('id')))
                    words = textblock("alto|String")
                    for word in words:
                        if updated_element.text.split(" ")[wordcount] != original_element.text.split(" ")[wordcount]:
                            # update ALTO & set the character confidence and word confidence to 100%
                            modified['alto'][alto_files[alto_connections[page][0]].barcode].append(
                                change_alto_attrib(original_element.get('id'), "WC", "1.00")
                            )
                            modified['alto'][alto_files[alto_connections[page][0]].barcode].append(
                                change_alto_attrib(original_element.get('id'), "CC", '0' * len(updated_element.text.split(" ")[wordcount]))
                            )
                            modified['alto'][alto_files[alto_connections[page][0]].barcode].append(
                                change_alto_attrib(original_element.get('id'), "CONTENT", updated_element.text.split(" ")[wordcount])
                            )
                        wordcount += 1
                modified['case']['changes'].append(change_casebody_content(original_element.get('id'), updated_element.text))
            else:
                modified['case']['changes'].append(change_case_content(xpath, readable_xpath, updated_element.text))

        # I don't think the stuff below should directly affect the ALTO

        # check if any attributes were added or removed
        if set(original_element.keys()) != set(updated_element.keys()):
            deleted_attributes = set(original_element.keys()) - set(updated_element.keys())
            added_attributes = set(updated_element.keys()) - set(original_element.keys())
            for attribute in deleted_attributes:
                if in_casebody:
                    modified['case']['changes'].append(delete_casebody_attrib(original_element.get('id'), attribute))
                else:
                    modified['case']['changes'].append(delete_case_attrib(xpath, readable_xpath, attribute))
            for attribute in added_attributes:
                if in_casebody:
                    modified['case']['changes'].append(change_casebody_attrib(original_element.get('id'), attribute))
                else:
                    modified['case']['changes'].append(change_case_attrib(xpath, readable_xpath, attribute))
                    
        # check to see if any attribute values changed
        for attribute in original_element.keys():
            if original_element.get(attribute) != updated_element.get(attribute):
                if in_casebody:
                    modified['case']['changes'].append(change_casebody_attrib(original_element.get('id'), attribute))
                else:
                    modified['case']['changes'].append(change_case_attrib(xpath, readable_xpath, attribute))
    

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

