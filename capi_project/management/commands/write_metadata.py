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
                error_raised = False
                with open(os.path.join(root, filename), 'rb') as f:
                    reader = csv.DictReader(f)
                    for i,row in enumerate(reader):
                        try:
                            models.Case.create_from_row(row)

                        except Exception as e:
                            raise CommandError('Something went wrong',e,i,row,os.path.join(root, filename))
                            error_raised = True
                            pass
                if not error_raised:
                    self.stdout.write(self.style.SUCCESS('Success', os.path.join(root, filename)))
