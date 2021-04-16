import base64
from pprint import pprint
import redis
import json

from django.conf import settings

from config.celery import app

"""
    Helpers to inspect and edit the celery job queue.
    Called from `fab celery_*`.
"""

def jobs_pending():
    """List all jobs not yet claimed by a worker."""
    r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    for queue in get_queues():
        print(f"Pending jobs for {queue}:")
        last_task = None
        tasks = []
        for i, job_json in enumerate(r.lrange(queue, 0, -1)):
            job, headers, id = parse_job(job_json)
            if headers['task'] != last_task:
                last_task = headers['task']
                tasks.append((last_task, i))
        if not tasks:
            print("- empty")
        else:
            tasks.append((None, i))
            for i, (task, index) in enumerate(tasks):
                if task:
                    print(f"- {task}: {index}-{tasks[i+1][1]}")


def job_info(index=0, queue='celery'):
    """Dump json info for a particular job."""
    r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    job_json = r.lindex(queue, index)
    job, headers, id = parse_job(job_json)
    job['body'] = json.loads(base64.b64decode(job['body']))
    pprint(job)


def remove_jobs(task_name, queue='celery'):
    """Remove all jobs with a given name from the queue."""
    r = redis.Redis.from_url(settings.CELERY_BROKER_URL)
    inspected = set()
    removed = 0
    while True:
        job_json = r.lpop(queue)
        job, headers, id = parse_job(job_json)
        if id in inspected:
            break
        inspected.add(id)
        if headers['task'] != task_name:
            r.rpush(queue, job_json)
        else:
            removed += 1
    print(f"Removed {removed} instances of {task_name}")


## helpers ##

def parse_job(job_json):
    task = json.loads(job_json)
    headers = task['headers']
    id = headers['id']
    return task, headers, id


def get_queues():
    queues = app.control.inspect().active_queues()
    return set(q['name'] for listen_queues in queues.values() for q in listen_queues)


