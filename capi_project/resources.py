import csv
from capi_project.models import Case

def create_metadata_from_csv(csv_doc):
    with open(csv_doc, 'rb') as f:
        reader = csv.DictReader(f)
        for row in reader:
            case = Case.create_from_row(row)
            case.save()
