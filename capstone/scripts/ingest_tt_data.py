from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.db import IntegrityError
from django.db.models import BooleanField

from tqdm import tqdm

from cap.models import Hollis as HollisDest
from cap.models import VolumeMetadata, TrackingToolUser, Reporter, ProcessStep, TrackingToolLog, BookRequest
from tracking_tool.models import BookRequests, Eventloggers, Hollis, Pstep, Reporters, Users, Volumes
"""
    Copies over 
"""

def ingest(dupcheck):

    """
    If we decide to copy more tables over, just add a new entry:
    copyModel(sourcemodel, destinationmodel, dupcheck)
    """

    copyModel(Users, TrackingToolUser, dupcheck)
    copyModel(BookRequests, BookRequest, dupcheck)
    copyModel(Pstep, ProcessStep, dupcheck, dupe_field='step_id')
    copyModel(Reporters, Reporter, dupcheck)
    copyModel(Hollis, HollisDest, dupcheck)
    copyModel(Volumes, VolumeMetadata, dupcheck, {
        'created_by': 'created_by_id',
    }, dupe_field='bar_code')
    copyModel(Eventloggers, TrackingToolLog, dupcheck, {
        'bar_code': 'volume_id',
        'created_by': 'created_by_id',
    })


def copyModel(source, destination, dupcheck, name_lookup={}, dupe_field='id'):
    """
    This essentially just copies all records in one table to another 
    table with the same column names.

    The only problem I had with the data was Django not correctly interpreting
    date fields that were set to 'allballs,' so I just went into the tracking
    tool db and ran:

    update eventloggers set updated_at = created_at 
    where updated_at = '0000-00-00 00:00:00+00';
    """
    print("Copying {} to {}".format(source.__name__, destination.__name__))

    # build dictionary of source fields
    source_fields = {field.name: field for field in source._meta.get_fields()}

    # build dictionary of destination fields, if they exist
    dest_fields = {}
    for field_name in source_fields.keys():
        dest_field_name = name_lookup.get(field_name, field_name)
        try:
            dest_fields[dest_field_name] = destination._meta.get_field(dest_field_name)
        except FieldDoesNotExist:
            pass

    source_collection=source.objects.all()
    if dupcheck:
        dupe_set = set(destination.objects.values_list(dupe_field, flat=True))
    for source_record in tqdm(source_collection, total=source_collection.count()):
        if dupcheck:
            if getattr(source_record, dupe_field) in dupe_set:
                continue

        destination_record = destination()
        for field_name, source_field in source_fields.items():
            # skip fields that don't exist on dest
            dest_field_name = name_lookup.get(field_name, field_name)
            dest_field = dest_fields.get(dest_field_name)
            if not dest_field:
                continue

            value = getattr(source_record, field_name)

            # special cases
            # null value in boolean field should be False
            if type(dest_field) == BooleanField:
                if not value or value == 'N':
                    value = False
                elif value == 'Y':
                    value = True

            # skip broken request_id links -- sources don't exist
            if field_name == 'request_id' and value in (53, 54, 55, 56):
                continue

            setattr(destination_record, dest_field_name, value)

        try:
            destination_record.save()
        except IntegrityError as e:
            print(e)