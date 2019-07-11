# Create your models here.
from django.db import models


class Gallery(models.Model):
    title = models.CharField(max_length=255) # markdown-formatted text
    content = models.TextField() # markdown-formatted text
    image_path = models.CharField(max_length=255)
    page_link = models.CharField(max_length=255, blank=True, null=True)
    repo_link = models.CharField(max_length=255, blank=True, null=True)
    order = models.IntegerField(unique=True, default=0)

    def __str__(self):
        return self.title
