from django.db import models

class Case(models.Model):
    caseid = models.CharField(primary_key=True, max_length=255)
    firstpage = models.IntegerField(null=True, blank=True)
    lastpage = models.IntegerField(null=True, blank=True)
    jurisdiction = models.CharField(max_length=100, blank=True)
    citation = models.CharField(max_length=255, blank=True)
    docketnumber = models.CharField(max_length=255, blank=True)
    decisiondate = models.DateField(null=True, blank=True)
    decisiondate_original = models.CharField(max_length=100, blank=True)
    court = models.TextField(blank=True)
    name = models.TextField(blank=True)
    court_abbreviation = models.CharField(max_length=255, blank=True)
    name_abbreviation = models.CharField(max_length=255, blank=True)
    volume = models.CharField(max_length=45, blank=True)

    @classmethod
    def create(self, caseid):
        case = self(caseid=caseid)
        return case

    @classmethod
    def create_from_row(self, row):
        case = self(
            caseid=row['caseid'],
            firstpage=row['firstpage'],
            lastpage=row['lastpage'],
            jurisdiction=row['jurisdiction'],
            citation=row['citation'],
            docketnumber=row['docketnumber'],
            decisiondate=row['decisiondate'],
            decisiondate_original=row['decisiondate_original'],
            court=row['court'],
            name=row['name'],
            court_abbreviation=row['court_abbreviation'],
            name_abbreviation=row['name_abbreviation'],
            volume=row['volume'],
        )
        return case
