# Create your models here.
from django.db import models


class Gallery(models.Model):
    title = models.CharField(max_length=255) # markdown-formatted text
    page_link = models.CharField(max_length=255, blank=True, null=True)
    repo_link = models.CharField(max_length=255, blank=True, null=True)
    content = models.TextField() # markdown-formatted text

    def __str__(self):
        return self.label
