# Create your models here.
from django.db import models
from db_file_storage.storage import DatabaseFileStorage
from django.utils.text import slugify


class GallerySection(models.Model):
    title = models.CharField(max_length=255)
    title_slug = models.CharField(max_length=255, null=True)
    order = models.IntegerField(default=10)

    def save(self, *args, generate_slug=True, **kwargs):
        if not self.title_slug or generate_slug:
            self.title_slug = slugify(self.title)
            return super().save(*args, **kwargs)
        else:
            return super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class GalleryEntry(models.Model):
    title = models.CharField(max_length=255)
    title_slug = models.CharField(max_length=255, null=True)
    section = models.ForeignKey(GallerySection, on_delete=models.DO_NOTHING, related_name='entries')
    content = models.TextField() # markdown-formatted text
    image = models.ImageField(
        # this looks wonky, but it seems like it's the way it's supposed to be. Each of these slash delimited fields
        # specifies the name of the field in CMSPicture which stores that information. Uploading 'whatever.jpg' yields
        # the file name 'capweb.CMSPicture/bytes/filename/mimetype/whatever.jpg'... the fields are not replaced with
        # their values
        upload_to='capweb.CMSPicture/bytes/filename/mimetype',
        storage=DatabaseFileStorage(),
        blank=True, null=True)
    page_link = models.CharField(max_length=255, blank=True, null=True)
    repo_link = models.CharField(max_length=255, blank=True, null=True)
    order = models.IntegerField(default=10)
    featured = models.BooleanField(default=True, null=False)

    def save(self, *args, generate_slug=True, **kwargs):
        if not self.title_slug or generate_slug:
            self.title_slug = slugify(self.title)
            return super().save(*args, **kwargs)
        else:
            return super().save(*args, **kwargs)

    def __str__(self):
        return self.title

class CMSPicture(models.Model):
    bytes = models.TextField()
    filename = models.CharField(max_length=255)
    mimetype = models.CharField(max_length=50)



