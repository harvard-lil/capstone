from celery import task

from capdb.models import VolumeXML, CaseXML
from scripts.helpers import chunked_iterator


def create_case_metadata_from_all_vols(update_existing=False):
    """
        iterate through all volumes, call celery task for each volume
    """
    volumes = VolumeXML.objects.all().order_by('id')
    for volume in chunked_iterator(volumes, chunk_size=200):
        create_case_metadata_from_vol.delay(volume.barcode, update_existing=update_existing)


@task
def create_case_metadata_from_vol(volume_barcode, update_existing=False):
    """
        create or update cases for each volume
    """
    casexmls = CaseXML.objects.filter(volume__barcode=volume_barcode).order_by('id')
    for casexml in chunked_iterator(casexmls, chunk_size=200):
        casexml.create_or_update_metadata(update_existing=update_existing)
