# Create your models here.
from django.db import models


class Gallery(models.Model):
    title = models.CharField(max_length=255)
    section = models.CharField(max_length=20, default="Applications")
    content = models.TextField() # markdown-formatted text
    image = models.ImageField(blank=True, null=True, upload_to="static/img/gallery/")
    page_link = models.CharField(max_length=255, blank=True, null=True)
    repo_link = models.CharField(max_length=255, blank=True, null=True)
    order = models.IntegerField(default=10)

    def __str__(self):
        return self.title
