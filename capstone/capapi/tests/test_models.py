from django.test import TestCase

import capapi.tests.helpers as helpers
from capapi.models import Reporter, CaseUser


class ModelTestCase(TestCase):
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

    def test_create_unique_reporter(self):
        reporter = Reporter.get_or_create_unique(name='Ill. 3d', jurisdiction='Illinois')
        assert reporter.slug == 'ill-3d'
        reporter = Reporter.get_or_create_unique(name='Ct. Cl.', jurisdiction='United States')
        assert reporter.slug == 'us-ct-cl'
        reporter = Reporter.get_or_create_unique(name='Smith', jurisdiction='New Hampshire')
        assert reporter.slug == 'nh-smith'


class CaseUserTestCase(TestCase):
    def setUp(self):
        helpers.setup_authenticated_user(email="boblawblaw@lawblog.com", first_name="Bob", last_name="Lawblaw", password="unique_password")

    def test_case_download_allowed(self):
        user = CaseUser.objects.get(email="boblawblaw@lawblog.com")
        assert user.case_allowance == 500
        assert user.case_download_allowed(10)
        assert not user.case_download_allowed(501)

