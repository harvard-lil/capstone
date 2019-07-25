# Create your models here.
from django.db import models
from db_file_storage.storage import DatabaseFileStorage

class GallerySection(models.Model):
    title = models.CharField(max_length=255)
    order = models.IntegerField(default=10)

    def __str__(self):
        return self.title

class GalleryEntry(models.Model):
    title = models.CharField(max_length=255)
    section = models.ForeignKey(GallerySection, on_delete=models.DO_NOTHING, related_name='entries')
    content = models.TextField() # markdown-formatted text
    image = models.ImageField(upload_to='capweb.CMSPicture/bytes/filename/mimetype', storage=DatabaseFileStorage(), blank=True, null=True)
    page_link = models.CharField(max_length=255, blank=True, null=True)
    repo_link = models.CharField(max_length=255, blank=True, null=True)
    order = models.IntegerField(default=10)

    def __str__(self):
        return self.title

class CMSPicture(models.Model):
    bytes = models.TextField()
    filename = models.CharField(max_length=255)
    mimetype = models.CharField(max_length=50)



