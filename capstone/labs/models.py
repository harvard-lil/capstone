import shortuuid
from django.db import models, transaction
from django.contrib.postgres.fields import JSONField
from capapi.models import CapUser


#======================== CHRONOLAWGIC


def get_short_uuid():
    return shortuuid.ShortUUID().random(length=10)

class Timeline(models.Model):
    created_by = models.ForeignKey(CapUser, on_delete=models.DO_NOTHING, related_name="timeline")
    uuid = models.CharField(max_length=10, default=get_short_uuid)
    timeline = JSONField(default=dict)

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
            return super(Timeline, self).save(*args, **kwargs)
