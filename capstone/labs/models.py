import uuid

from django.db import models, IntegrityError, transaction
from django.contrib.postgres.fields import JSONField
from capapi.models import CapUser

#======================== CHRONOLAWGIC


class Timeline(models.Model):
    created_by = models.ForeignKey(CapUser, on_delete=models.DO_NOTHING, related_name="timeline")
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    timeline = JSONField(default=dict)

    def save(self, bypass_uuid_check=False, *args, **kwargs):
        attempts = 0
        while attempts < 5:
            try:
                with transaction.atomic():
                    return super(Timeline, self).save(*args, **kwargs)
            except IntegrityError as e:
                attempts += 1
                if attempts > 4:
                    raise
                self.code = uuid.uuid4()

        raise IntegrityError("Could Not Save Timeline")