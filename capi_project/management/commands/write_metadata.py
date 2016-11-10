import os
import csv
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    can_import_settings = True

    def handle(self, *args, **options):
        from django.conf import settings
        from capi_project import models

        for root, dirs, files in os.walk(settings.METADATA_DIR_PATH):
            for filename in files:
                with open(os.path.join(root, filename), 'rb') as f:
                    reader = csv.DictReader(f)
                    try:
                        map(models.Case.create_from_row, reader)
                    except Exception as e:
                        raise CommandError('Something went wrong',os.path.join(root, filename))
                        pass

                self.stdout.write(self.style.SUCCESS('Success'))
