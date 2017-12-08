from celery import shared_task

from capdb.models import VolumeXML, CaseXML
from scripts.helpers import chunked_iterator


def create_case_metadata_from_all_vols(update_existing=False):
    """
        iterate through all volumes, call celery task for each volume
    """
    volumes = VolumeXML.objects.all().order_by('id')
    for volume in chunked_iterator(volumes, chunk_size=200):
        create_case_metadata_from_vol.delay(volume.barcode, update_existing=update_existing)


@shared_task
def create_case_metadata_from_vol(volume_barcode, update_existing=False):
    """
        create or update cases for each volume
    """
    casexmls = CaseXML.objects.filter(volume__barcode=volume_barcode).order_by('id')
    for casexml in chunked_iterator(casexmls, chunk_size=200):
        casexml.create_or_update_metadata(update_existing=update_existing)


@shared_task
def test_slow(i, ram=10, cpu=30):
    """
        Waste a bunch of memory and CPU.
    """
    print("Task %s" % i)
    # waste 0-ram MB of RAM
    waste_ram = bytearray(2**20 * i%ram)  # noqa

    # waste CPU
    total = 0
    for i in range(cpu * 1000000):
        total += i
