from django.db import models
from django.contrib.postgres.fields import JSONField
from capapi.models import CapUser

#======================== CHRONOLAWGIC

class TimeLine(models.Model):
    created_by = models.ForeignKey(CapUser, on_delete=models.DO_NOTHING, related_name="timeline")
    timeline = JSONField(default=dict)
