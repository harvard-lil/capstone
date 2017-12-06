import random
import time
from celery import shared_task


@shared_task
def test_slow(ram=10, cpu=10):
    """
        Waste a bunch of memory and CPU.
    """
    # waste 1-ram MB of RAM
    waste_ram = bytearray(2**20 * random.randint(1, ram))  # noqa

    # waste 1-10 seconds of CPU at 50% usage
    end_time = time.time() + random.randint(1, cpu)
    while time.time() < end_time:
        step_time = time.time() + .01
        while time.time() < step_time:
            foo = sum(i for i in range(1000000))  # noqa
        time.sleep(.01)

