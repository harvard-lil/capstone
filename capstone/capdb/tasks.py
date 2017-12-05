import random
import time
from celery import shared_task


@shared_task
def test_slow(*args):
    """
        Waste a bunch of memory and CPU.
    """
    # waste 1-10MB of RAM
    waste_ram = bytearray(2**20 * random.randint(1, 10))  # noqa

    # waste 1-10 seconds of CPU
    end_time = time.time() + random.randint(1, 10)
    while time.time() < end_time:
        foo = sum(i for i in range(10000000))  # noqa

