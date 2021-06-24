import shortuuid
from django.db import models, transaction
from capapi.models import CapUser


#======================== CHRONOLAWGIC


def get_short_uuid():
    return shortuuid.ShortUUID().random(length=10)


class Timeline(models.Model):
    created_by = models.ForeignKey(CapUser, on_delete=models.DO_NOTHING, related_name="timeline")
    uuid = models.CharField(max_length=10, default=get_short_uuid, unique=True)
    timeline = models.JSONField(default=dict)

    def save(self, bypass_uuid_check=False, *args, **kwargs):
        if self._state.adding or bypass_uuid_check:
            collision = Timeline.objects.filter(uuid=self.uuid).count() > 0
            attempts = 0
            while collision:
                if attempts > 4:
                    raise Exception('Cannot generate unique timeline id')
                attempts += 1
                new_uuid = get_short_uuid()
                self.uuid = new_uuid
                collision = Timeline.objects.filter(uuid=self.uuid).count() > 0
        with transaction.atomic():
            valid, errors = self.normalize_and_validate_timeline()
            if not valid:
                raise TimelineValidationException(errors)
            return super(Timeline, self).save(*args, **kwargs)

    #
    #
    # Use these add_update/update_/delete methods to modify the timeline validated and saved
    #
    #

    def update_timeline_metadata(self, updated_timeline):
        for field in self.timeline_metadata_fields():
            self.timeline[field] = updated_timeline[field]
        return self.save()

    # subobject is the actual new/updated case or whatever. 
    # type is the key in the schemas variable
    def add_update_subobject(self, subobject, type):
        if subobject['id'] in self.subobject_ids(type):
            self.timeline[type].append(subobject)
        else:
            self.timeline[type] = [existing if existing['id'] != subobject['id'] else subobject
                                   for existing in self.timeline[type]]
        return self.save()
    
    def delete_subobject(self, type, subobject_id):
        self.timeline[type] = [existing for existing in self.timeline[type] if existing['id'] != subobject_id]
        return self.save()

    schemas = {
        'timeline': [
            {'name': 'title', 'type': str, 'required': True, 'default': 'Untitled Timeline'},
            {'name': 'author', 'type': str, 'required': True, 'default': 'CAP user'},
            {'name': 'description', 'type': str, 'required': False},
            {'name': 'cases', 'type': list, 'required': False},
            {'name': 'events', 'type': list, 'required': False},
            {'name': 'categories', 'type': list, 'required': False},
            {'name': 'first_year', 'type': int, 'required': False},
            {'name': 'last_year', 'type': int, 'required': False},
            {'name': 'stats', 'type': list, 'required': False},
        ],
        'subobjects': {
            'events': [
                {'name': 'id', 'type': str, 'required': True},
                {'name': 'name', 'type': str, 'required': True},
                {'name': 'short_description', 'type': str, 'required': False},
                {'name': 'long_description', 'type': str, 'required': False},
                {'name': 'start_date', 'type': str, 'required': True},
                {'name': 'end_date', 'type': str, 'required': True},
                {'name': 'color', 'type': str, 'required': False},
                {'name': 'categories', 'type': list, 'required': False},
                {'name': 'url', 'type': str, 'required': False},
            ],
            'cases': [
                {'name': 'id', 'type': str, 'required': True},
                {'name': 'name', 'type': str, 'required': True},
                {'name': 'short_description', 'type': str, 'required': False},
                {'name': 'long_description', 'type': str, 'required': False},
                {'name': 'jurisdiction', 'type': str, 'required': False},
                {'name': 'decision_date', 'type': str, 'required': True},
                {'name': 'reporter', 'type': str, 'required': False},
                {'name': 'court', 'type': str, 'required': False},
                {'name': 'url', 'type': str, 'required': False},
                {'name': 'citation', 'type': str, 'required': False},
                {'name': 'categories', 'type': list, 'required': False},
                {'name': 'color', 'type': str, 'required': False},
            ],
            'categories': [
                {'name': 'id', 'type': str, 'required': True},
                {'name': 'name', 'type': str, 'required': True},
                {'name': 'color', 'type': str, 'required': True},
                {'name': 'shape', 'type': str, 'required': True},
            ]
        }
    }

    def case_stats(self):
        return

    @staticmethod
    def generate_empty_timeline():
        return { field['name']: (field['default'] if 'default' in field else field['type']())
                 for field in Timeline.schemas['timeline']}

    @staticmethod
    def subobject_types():
        return Timeline.schemas['subobjects'].keys()

    @staticmethod
    def timeline_metadata_fields():
        return [field['name'] for field in Timeline.schemas['timeline'] if field['type'] != list]

    def subobject_ids(self, type):
        return [subobj['id'] for subobj in self.timeline[type]]

    def normalize_and_validate_timeline(self):
        if not self.timeline:
            Timeline.generate_empty_timeline()
            return [True, []]
        bad = {
            'timeline': self.normalize_and_validate_single_object('timeline', self.timeline)
        }
        for subobject_type in Timeline.subobject_types():
            bad[type] = []
            for index, entry in enumerate(self.timeline[subobject_type]):
                self.timeline[subobject_type][index], bad[type][index] = self.normalize_and_validate_single_object(
                    subobject_type, entry)
            if bad[type] == []:
                del bad[type]
        return [False if bad else True, bad]

    # also validates the MD fields in the timeline itself
    def normalize_and_validate_single_object(self, type, entry, name, normalize=True):
        local_bad = []

        if type == 'timeline':
            fields = self.schemas['timeline']
        else:
            fields = self.schemas['subobjects'][type]

        # is this even the right thing?
        if type(entry) != dict:
            return [entry, ["Wrong Data Type for {} entry: {} instead of dict".format(name, type(entry))]]

        # do we have extra fields?
        known_field_names = [field['name'] for field in fields]
        extraneous = set(entry.keys()) - set(known_field_names)
        for extraneous_field in extraneous:
            if not entry[extraneous_field] and normalize:  # if the field is empty, just remove it
                del entry[extraneous_field]
                entry.remove(extraneous_field)

        if extraneous:
            local_bad.append("Unexpected {} field(s): {}. Expecting {}".format(
                name,
                extraneous,
                known_field_names
            ))

        # do we have every field, and are they the correct data type?
        for field in fields:
            if field['name'] not in entry:
                if 'default' in field and normalize:
                    entry[field['name']] = field['default']
                elif not field['required'] and normalize:
                    entry[field['name']] = field['type']()
                else: # definitely need this
                    local_bad.append("Missing {} field {}".format(name, field['name']))
            elif type(entry[field['name']]) != field['type']:
                if 'default' in field and normalize:
                    entry[field['name']] = field['default']
                elif not field['required'] or not entry[field['name']] and normalize:
                    entry[field['name']] = field['type']()
                else:  # definitely need this
                    local_bad.append("Wrong Data Type for {}. Should be {}. Value: {}".format(
                    field['name'], field['type'], entry[field['name']]))
            elif entry[field['name']] == '' and 'default' in field and normalize:
                entry[field['name']] = field['default']
        return [entry, local_bad]



class TimelineValidationException(Exception):
    pass