import pytest

from capweb.models import GallerySection, GalleryEntry, CMSPicture
from django.core.files.uploadedfile import SimpleUploadedFile

@pytest.mark.django_db
def test_cms_image_storage():
    section = GallerySection(
        title = "Test Title"
    )
    section.save()

    image = SimpleUploadedFile('capweb.CMSPicture/bytes/filename/mimetype/test.jpg', b'A pretty, pretty picture!')

    assert CMSPicture.objects.count() == 0
    entry = GalleryEntry(
        title="test",
        section=section,
        content="test",
        image=image,
    )
    entry.save()

    assert CMSPicture.objects.count() == 1
