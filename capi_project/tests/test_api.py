from django.test import TestCase
from capi_project.models import Case

from rest_framework.test import APIRequestFactory
from django.test import Client

import json

class CaseTestCase(TestCase):
    def setUp(self):
        case = Case.create(caseid=1,firstpage=21,lastpage=25,jurisdiction="Illinois",citation="177 Ill. 2d 21",docketnumber="No. 81291",decisiondate="1997-06-19",court="Illinois Supreme Court",name="TRANS STATES AIRLINES, Appellee, v. PRATT & WHITNEY CANADA, INC., Appellant",court_abbreviation="Ill.",name_abbreviation="Trans States Airlines v. Pratt & Whitney Canada, Inc.",volume="177",reporter="Ill. 2d",)
        case = Case.create(caseid=2,firstpage=166,lastpage=184,jurisdiction="New York",citation="229 A.D.2d 313",docketnumber="",decisiondate="1996-07-02",decisiondate_original="1996-07-02",court="New York Supreme Court, Appellate Division",name="Angelo Ramirez, Appellant, v. New York City School Construction Authority, Respondent, et al., Defendant",court_abbreviation="N.Y. App. Div.",name_abbreviation="Ramirez v. New York City School Construction Authority",volume="229",reporter="A.D.2d")

    def test_api_urls(self):
        c = Client()
        response = c.get('/cases/')
        assert response.status_code == 200
        assert response.accepted_renderer.format != 'json'
        response = c.get('/cases/?format=json')
        assert response.status_code == 200
        assert response.accepted_renderer.format == 'json'
        response = c.get('/cases/jurisdictions')
        assert response.accepted_renderer.format != 'json'
        assert response.status_code == 200
        response = c.get('/cases/jurisdictions?format=json')
        assert response.status_code == 200
        assert response.accepted_renderer.format == 'json'

    def test_jurisdictions(self):
        c = Client()
        response = c.get('/cases/jurisdictions?format=json')
        assert response.status_code == 200
        assert response.accepted_renderer.format == 'json'
        jurisdictions = json.loads(response.content)
        assert len(jurisdictions) == 2
        assert "New York" in jurisdictions

    def test_case(self):
        c = Client()
        response = c.get('/cases/Illinois/Ill%2E%202d?format=json')
        assert response.status_code == 200
        assert response.accepted_renderer.format == 'json'
        content = json.loads(response.content)
        case = content.get('results')[0]
        assert case.get('name_abbreviation') == 'Trans States Airlines v. Pratt & Whitney Canada, Inc.'

    
