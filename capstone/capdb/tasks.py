from celery import shared_task

from capdb.models import VolumeXML, CaseXML


def create_case_metadata_from_all_vols(update_existing=False):
    """
        iterate through all volumes, call celery task for each volume
    """
    for volume_id in VolumeXML.objects.values_list('pk', flat=True):
        create_case_metadata_from_vol.delay(volume_id, update_existing=update_existing)


@shared_task
def create_case_metadata_from_vol(volume_id, update_existing=False):
    """
        create or update cases for each volume
    """
    for casexml in CaseXML.objects.filter(volume_id=volume_id).defer_xml():
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
