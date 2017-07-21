import json

from django.test import TestCase, Client
from django.conf import settings

from capapi.models import Case
from capapi.tests import helpers

FULL_API_URL = settings.FULL_API_URL


class MetadataTestCase(TestCase):
    def setUp(self):
        jur_ill = helpers.setup_jurisdiction(id=2, name='Illinois', name_abbreviation='Ill.', slug='ill')
        jur_ny = helpers.setup_jurisdiction(id=1, name='New York', name_abbreviation='N.Y.', slug='ny')

        rep_ill = helpers.setup_reporter(id=1, name='Ill. 2d', name_abbreviation='Ill.2d', slug='ill-2d',
                                         start_date=1883, end_date=1901, jurisdiction=jur_ill, )
        rep_ny = helpers.setup_reporter(id=2, name='NY. App. 4th', name_abbreviation='ny.app.4', start_date=1984,
                                        end_date=1999, jurisdiction=jur_ny, )

        court_ill = helpers.setup_court(id=1, name="Illinois Supreme Court", name_abbreviation="Ill.", )
        court_ny = helpers.setup_court(id=2, name="New York Supreme Court, Appellate Division",
                                       name_abbreviation="N.Y. App. Div.", )

        helpers.setup_case(caseid=1, firstpage=21, lastpage=25, jurisdiction=jur_ill, citation="177 Ill. 2d 21",
                           docketnumber="No. 81291", decisiondate="1997-06-19",
                           name="TRANS STATES AIRLINES, Appellee, v. PRATT & WHITNEY CANADA, INC., Appellant",
                           name_abbreviation="Trans States Airlines v. Pratt & Whitney Canada, Inc.", volume="177",
                           reporter=rep_ill, court=court_ill)
        helpers.setup_case(caseid=2, firstpage=166, lastpage=184, jurisdiction=jur_ny, citation="229 A.D.2d 313",
                           docketnumber="", decisiondate="1996-07-02", decisiondate_original="1996-07-02",
                           name="Angelo Ramirez, Appellant, v. New York City School Construction Authority, Respondent, et al., Defendant",
                           name_abbreviation="Ramirez v. New York City School Construction Authority", volume="229",
                           reporter=rep_ny, court=court_ny)

    def test_api_urls(self):
        c = Client()
        response = c.get('%s/cases/' % settings.FULL_API_URL)
        assert response.status_code == 200
        assert response.accepted_renderer.format != 'json'
        response = c.get('%s/cases/?format=json' % settings.FULL_API_URL)
        assert response.status_code == 200
        assert response.accepted_renderer.format == 'json'
        response = c.get('%s/jurisdictions/' % settings.FULL_API_URL)
        assert response.accepted_renderer.format != 'json'
        assert response.status_code == 200
        response = c.get('%s/jurisdictions/?format=json' % settings.FULL_API_URL)
        assert response.status_code == 200
        assert response.accepted_renderer.format == 'json'

    def test_jurisdictions(self):
        c = Client()
        response = c.get("%s/jurisdictions/?format=json" % settings.FULL_API_URL)
        assert response.status_code == 200
        assert response.accepted_renderer.format == "json"
        results = json.loads(response.content)
        jurisdictions = results["results"]
        assert len(jurisdictions) == 2
        assert jurisdictions[1]["name"] == "New York"

    def test_case(self):
        c = Client()
        case = Case.objects.get(caseid=1)
        response = c.get("%s/cases/%s/?format=json" % (settings.FULL_API_URL, case.slug))
        assert response.status_code == 200
        assert response.accepted_renderer.format == "json"
        content = json.loads(response.content)
        assert content.get("name_abbreviation") == case.name_abbreviation

    def test_court(self):
        c = Client()
        response = c.get("%s/courts/?format=json" % settings.FULL_API_URL)
        assert response.status_code == 200
        assert response.accepted_renderer.format == "json"
        results = json.loads(response.content)
        assert len(results["results"]) == 2

    def test_reporter(self):
        c = Client()
        response = c.get("%s/reporters/?format=json" % settings.FULL_API_URL)
        assert response.status_code == 200
        assert response.accepted_renderer.format == "json"
        results = json.loads(response.content)
        assert len(results["results"]) == 2
