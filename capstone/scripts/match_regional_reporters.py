# one-off script to find the official state reporter that leaves off earliest for each regional reporter

import csv
from io import StringIO

from reporters_db import STATE_ABBREVIATIONS

from capapi.documents import CaseDocument
from capdb.models import Reporter

states = {v: k for k, v in STATE_ABBREVIATIONS.items()}

reporters_csv = """
Reporter	States	Short Codes	Start Delivery	End Delivery
A.3d	Connecticut, Delaware, District of Columbia, Maine, Maryland, New Hampshire, New Jersey, Pennsylvania, Rhode Island, Vermont			213
B.R.			583	603
Cal.Rptr.		Cal. 5th, Cal. App. 5th		251
F.3d			882	935
F.Supp.3d			282	392
N.E.3d	Illinois, Indiana, Massachusetts, New York, Ohio			130
N.W.2d	Iowa, Michigan, Minnesota, Nebraska, North Dakota, South Dakota, Wisconsin			932
N.Y.S.3d		N.Y.3d		105
P.3d	Alaska, Arizona, California, Colorado, Hawaii, Idaho, Kansas, Montana, Nevada, New Mexico, Oklahoma, Oregon, Utah, Washington, Wyoming			447
S.E.2d	Georgia, North Carolina, South Carolina, Virginia, West Virginia			831
S.W.3d			538	579
So.3d			236	276
U.S.			569	572
S.Ct.		U.S.		193
""".strip()

reporters = list(csv.DictReader(StringIO(reporters_csv), delimiter='\t'))

date_checks = {
    "A.3d": [
        515, 178,  # CT
        521, 524,  # MD
        489,  # NH
        558,  # NJ
    ],
    "N.E.3d": [
        322, 529,  # IL
        568, 478,  # MA
        22,  # NY
        546,  # OH
    ],
    "N.W.2d": [
        747, 520,  # MI
        672, 539,  # NE
        485,  # WI
    ],
    "P.3d": [
        291,  # AZ
        1078, 1082,  # CA
        423,  # HI
        306,  # ID
        472, 476,  # KS
        289,  # MT
        518,  # NV
        1028, 554,  # NM
        288, 411,  # OR
        477, 410,  # WA
    ],
    "S.E.2d": [
        519, 360,  # GA
        365, 549,  # NC
        282,  # SC
        383, 534,  # VA (weird 2004 end date)
        370,  # WV
    ],
}


def main():
    for reporter in reporters:
        print(reporter['Reporter'])


        # get regional reporter
        reporter_obj = Reporter.objects.filter(short_name=reporter['Reporter']).first()
        if reporter_obj:
            last_vol = reporter_obj.volumes.exclude(volume_number=None).filter(out_of_scope=False).order_by('-volume_number').first()
            if last_vol:
                # first_missing_vol = int(last_vol.volume_number) + 1
                print(f"- Last scan was {last_vol.volume_number} {last_vol.reporter.short_name} ({last_vol.publication_year})")
            else:
                print("- No volumes for regional reporter")
        else:
            print("- No regional reporter found")

        # skip series already answered
        if reporter['Start Delivery']:
            print(f"- Requesting from {reporter['Start Delivery']}")
            continue

        # print reporter candidates
        # if reporter['States']:
        #     states = reporter['States'].split(", ")
        #     for state in states:
        #         print("-", state)
        #         jurisdiction = Jurisdiction.objects.get(name_long=state)
        #         candidates = jurisdiction.reporter_set.filter(end_year__gt=2000)
        #         print(" -", state, candidates)

        if reporter['Reporter'] in date_checks:
            reporter_ids = date_checks[reporter['Reporter']]
            print("HEY", ", ".join(Reporter.objects.get(pk=i).short_name for i in reporter_ids))
        elif reporter['Short Codes']:
            reporter_ids = [Reporter.objects.get(short_name=s).pk for s in reporter['Short Codes'].split(", ")]
        else:
            raise Exception("No reporter IDs to check")

        for reporter_id in reporter_ids:
            official_reporter = Reporter.objects.get(pk=reporter_id)
            cases = CaseDocument.search().filter("term", reporter__id=reporter_id).sort('-decision_date').source(['decision_date'])[:1]
            decision_date = list(cases)[0].decision_date
            print(" -", official_reporter.short_name, decision_date)
