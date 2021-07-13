import io
import csv
from collections import defaultdict

from django.db.models import Count, Q
from capdb.models import Reporter, Jurisdiction, CaseMetadata
from capweb.templatetags.api_url import api_url
from tqdm import tqdm
from capdb.storages import download_files_storage

def update_all():
    cases_by_jurisdiction_tsv()
    cases_by_reporter_tsv()
    cases_by_decision_date_tsv()


def cases_by_decision_date_tsv(directory=""):
    """
        count of all cases, grouped by decision date
    """
    by_date = (CaseMetadata.objects
        .in_scope()
        .values('decision_date_original')
        .annotate(Count('decision_date_original'))
        .order_by('decision_date_original'))
    label="cases_by_decision_date"
    snippet_format="tsv"
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t', quoting=csv.QUOTE_NONNUMERIC)

    # count dates
    date_counter = defaultdict(int)
    for group in tqdm(by_date):
        date = group['decision_date_original']
        count = group['decision_date_original__count']
        # count year
        date_counter[date[:4]] += count
        # count year-month
        if len(date) > 4:
            date_counter[date[:7]] += count
        # count year-month-day
        if len(date) > 7:
            date_counter[date] += count

    # write dates
    cases_url = api_url('cases-list')
    for date, count in date_counter.items():
        max_date = date + "0000-12-31"[len(date):]
        writer.writerow([
            date,
            count,
            f"{cases_url}?decision_date__gte={date}&decision_date__lte={max_date}",
        ])

    write_update(label, snippet_format, output.getvalue(), directory=directory)


def cases_by_jurisdiction_tsv(directory=""):
    """
        iterate through all reporters, tally each case, output TSV
    """
    label="cases_by_jurisdiction"
    snippet_format="tsv"
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t',quoting=csv.QUOTE_NONNUMERIC)
    for jurisdiction in tqdm(Jurisdiction.objects.order_by('name').annotate(case_count=Count('case_metadatas', filter=Q(case_metadatas__in_scope=True)))):
        if jurisdiction.case_count == 0:
            continue
        writer.writerow(
            [
                jurisdiction.name,
                jurisdiction.name_long,
                jurisdiction.case_count,
                "{}?jurisdiction={}".format(api_url('cases-list'), jurisdiction.slug),
                "{}{}".format(api_url('jurisdiction-list'), jurisdiction.pk)
            ]
        )

    write_update(label, snippet_format, output.getvalue(), directory=directory)


def cases_by_reporter_tsv(directory=""):
    """
        iterate through all jurisdictions, tally each case, output TSV
    """
    label="cases_by_reporter"
    snippet_format="tsv"
    output = io.StringIO()
    writer = csv.writer(output, delimiter='\t',quoting=csv.QUOTE_NONNUMERIC)
    for reporter in tqdm(Reporter.objects.order_by('full_name').annotate(case_count=Count('case_metadatas', filter=Q(case_metadatas__in_scope=True)))):
        if reporter.case_count == 0:
            continue
        writer.writerow(
            [
                reporter.short_name,
                reporter.full_name,
                reporter.case_count,
                "{}?reporter={}".format(api_url('cases-list'), reporter.pk),
                "{}{}".format(api_url('reporter-list'), reporter.pk)
            ]
        )

    write_update(label, snippet_format, output.getvalue(), directory=directory)


def write_update(label, snippet_format, contents, directory):

    file_name = "{}.{}".format(label, snippet_format)
    full_path = "{}{}{}".format(directory, '/' if directory else '', file_name)

    if directory and not download_files_storage.exists(directory):
        download_files_storage.mkdir(directory, parents=True)

    with download_files_storage.open(full_path, 'w') as d:
        d.write(contents)
