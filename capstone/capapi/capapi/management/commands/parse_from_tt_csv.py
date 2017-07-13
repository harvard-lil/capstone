import os
import sys
import csv
from django.core.management.base import BaseCommand, CommandError
from django.db import models

class Command(BaseCommand):
    can_import_settings = True

    def add_arguments(self, parser):
        parser.add_argument('filename', type=str)
        parser.add_argument('model', type=str)

    def handle(self, *args, **options):
        from capapi.models import Reporter, Volume, Jurisdiction
        filename = options['filename']
        model = options['model']
        with open(filename, 'rU') as f:
            reader = csv.DictReader(f)
            for i,row in enumerate(reader):
                if model == 'Reporter':
                    Reporter.create_from_tt_row(row)
                elif model == 'Volume':
                    Volume.create_from_tt_row(i, row)
                elif model == 'Jurisdiction':
                    Jurisdiction.create_from_tt_row(row)
