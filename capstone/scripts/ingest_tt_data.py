from django.conf import settings
from django.db import transaction, IntegrityError

from tqdm import tqdm

from cap.models import Hollis as HollisDest
from cap.models import VolumeMetadata, TrackingToolUsers, Reporter, ProcessStep, TrackingToolLog, Batch, BookRequest
from tracking_tool.models import Batches, BookRequests, Eventloggers, Hollis, Pstep, Reporters, Users, Volumes
"""
    Copies over 
"""

def ingest(dupcheck):

    """
    If we decide to copy more tables over, just add a new entry:
    copyModel(sourcemodel, destinationmodel, dupcheck)
    """

    copyModel(Volumes, VolumeMetadata, dupcheck)
    copyModel(Users, TrackingToolUsers, dupcheck)
    copyModel(Reporters, Reporter, dupcheck)
    copyModel(Hollis, HollisDest, dupcheck)
    copyModel(Batches, Batch, dupcheck)
    copyModel(BookRequests, BookRequest, dupcheck)
    copyModel(Pstep, ProcessStep, dupcheck)
    copyModel(Eventloggers, TrackingToolLog, dupcheck)


def copyModel(source, destination, dupcheck):
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
    
    source_collection=source.objects.all()
    pbar = tqdm(total=source_collection.count())
    for source_record in source_collection:
        if dupcheck == True:
            if hasattr(source_record, 'id'):
                created = destination.objects.filter(id=source_record.id).exists()
            elif hasattr(source_record, 'bar_code'):
                created = destination.objects.filter(bar_code=source_record.bar_code).exists()
            elif hasattr(source_record, 'step_id'):
                created = destination.objects.filter(step_id=source_record.step_id).exists()
            else:
                raise("Unrecognized ID in existence check")
            
            if created:
                pbar.update(1)
                continue

        destination_record = destination()
        for field in source._meta.get_fields():
            setattr(destination_record, field.name, getattr(source_record, field.name))
        destination_record.save()
        pbar.update(1)
    pbar.close()