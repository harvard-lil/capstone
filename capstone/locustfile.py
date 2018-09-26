import json
import math
from random import randint, choice
from locust import HttpLocust, TaskSet, task

generated_user_first_name = "FAKE_USER_DELETE_ME_999"
generated_user_last_name = "FAKE_USER_DELETE_ME_999"
generated_user_password= "This Is A Fake {} Password!".format(randint(0,999999))
generated_user_email_template = "fake_user_{}@{}.{}"

confirmed_test_user_email = "tester_999_joe@case.test"
confirmed_test_user_password = ""

api_host = "api.capapi.org"

endpoints = ["cases"]

static_paths = ["about/", "terms", "tools/", "api/", "bulk/", "gallery/", "gallery/wordclouds", "gallery/limericks",
                "user/login", "user/register", "contact/", ""]


jurisdictions = [ "ala", "alaska", "am-samoa", "ariz", "cal", "colo", "conn", "dakota-territory", "dc", "del", "fla",
    "ga", "guam", "haw", "idaho", "ind", "iowa", "kan", "ky", "la", "mass", "md", "me", "mich", "minn", "miss", "mo",
    "mont", "native-american", "navajo-nation", "nc", "nd", "neb", "nev", "nh", "nj", "nm", "n-mar-i", "ny", "ohio",
    "okla", "or", "pa", "pr", "regional", "ri", "sc", "sd", "tenn", "tex", "us", "utah", "va", "vi", "vt", "wash",
    "wis", "w-va", "wyo", "ill", "ark"]

search_terms = ["AKA", "Accelerated%20Rehabilitation", "Acknowledgment", "Action", "Adjournment", "Adjudication",
            "Adjudicatory%20Hearing", "Adult%20Court%20Transfer", "Adult%20Probation", "Affidavit", "Affirmation",
            "Alcohol%20Education%20Program", "Alford%20Doctrine", "Alimony", "Allegation", "Alternate%20Juror",
            "Alternative%20Detention%20Program", "Alternative%20Dispute%20Resolution",
            "Alternative%20Incarceration%20Center", "Alternative%20Sanctions", "Amicus%20Curiae%20brief", "Annulment",
            "Answer", "Appeal", "Appeal%20Bond", "Appearance", "Appellant", "Appellee", "Arbitration", "Arraignment",
            "Arrearages", "Arrest", "Assignment%20List", "Assistant%20Attorney%20General", "Attachment",
            "Attorney%20of%20Record", "Automatic%20Orders", "Bail", "Bail%20Bondsperson", "Bail%20Commissioner", "Bar",
            "Bench%20Warrant", "Best%20Interest%20of%20the%20Child", "Bond", "Bond%20Forfeiture%20", "Bond%20Review",
            "Bondsman", "Brief", "Broken%20Down%20Irretrievably", "CGS", "CIP", "Calendar", "Calendar%20Call",
            "Capias%20Mittimus", "Capital%20Felony", "Case", "Case%20Conference", "Case%20File",
            "Case%20Flow%20Coordinator", "Central%20Transportation%20Unit", "Certify", "Challenge", "Charge",
            "Charge%20to%20Jury", "Chattels", "Child", "Child%20Support", "Civil%20Action", "Claim",
            "Classification%20and%20Program%20Officer", "Common%20Law", "Community%20Service",
            "Community%20Service%20Labor%20Program", "Community%20Services%20Coordinator", "Complaint",
            "Complex%20Litigation", "Conditional%20Discharge", "Contempt%20of%20Court", "Continuance",
            "Continuance%20Date", "Contract", "Conviction", "Costs", "Count", "Counter%20Claim", "Court%20Clerk",
            "Court%20Interpreter", "Court%20Monitor", "Court%20Reporter", "Court%20Services%20Officer", "Court%20Trial",
            "Court-Appointed%20Attorney", "Crime%20Victim%20Compensation%20Program", "Cross-Examination", "Custody",
            "Custody%20Affidavit", "Damages", "Day%20Incarceration%20Center", "Declaration", "Default", "Defendant",
            "Delinquent", "Deposition", "Detention%20Hearing", "Detention%20Release%20Hearing", "Discovery",
            "Dismissal", "Dismissal%20Without%20Prejudice", "Dispose", "Disposition", "Dissolution",
            "Diversionary%20Programs", "Docket", "Docket%20Number", "Domicile", "Drug%20Court", "Education%20Program",
            "Ejectment", "Electronic%20Monitoring", "Emancipated%20Minor", "Emancipation", "Eminent%20Domain",
            "Eviction", "Evidence", "Ex%20Parte", "Execution%20Suspended", "Failure%20to%20Appear",
            "Family%20Relations%20Counselor", "Family%20Support%20Magistrate",
            "Family%20Violence%20Education%20Program", "Family%20Violence%20Victim%20Advocate",
            "Family%20With%20Service%20Needs", "Felony", "Felony%20Murder", "Filing", "Financial%20Affidavit",
            "Finding", "Foreclosure", "Foreman", "GA%20-%20Geographical%20Area", "Garnishment", "Grievance", "Guardian",
            "Guardian%20Ad%20Litem", "Habeas%20Corpus", "Hearsay", "Honor%20Court", "Housing%20Specialist",
            "Hung%20Jury", "Incarceration", "Income%20Withholding%20Order", "Indigent", "Information%20", "Infraction",
            "Injunction", "Interpreter", "Interrogatory", "Investigatory%20Grand%20Jury",
            "JD%20-%20Judicial%20District", "Judge", "Judgment", "Judgment%20File", "Juris%20Number", "Jurisdiction",
            "Juror", "Jury%20Charge", "Jury%20Instructions", "Juvenile%20Court", "Juvenile%20Delinquent",
            "Juvenile%20Detention", "Juvenile%20Detention%20Center", "Juvenile%20Detention%20Officer",
            "Juvenile%20Matters", "Juvenile%20Probation", "Juvenile%20Transportation%20Officer", "Law%20Librarian",
            "Legal%20Aid", "Legal%20Services", "Legal%20Custody", "Legal%20Separation", "Lien", "Lis%20Pendens",
            "Litigant", "Lockout", "Magistrate", "Mandamus", "Marshal", "Mediation", "Minor", "Misdemeanor",
            "Mitigating%20Circumstances", "Mittimus%20Judgment", "Modification", "Motion", "Movant", "Moving%20Party",
            "Ne%20Exeat", "Neglected%20Minor", "No%20Contact%20Order", "No%20Contest", "No%20Fault%20Divorce", "Nolle",
            "Nolo%20Contendere", "Non-Suit", "Non-financial%20bonds", "Notarize", "Oath",
            "Office%20of%20Adult%20Probation", "Order", "Order%20of%20Detention%20", "Order%20to%20Detain",
            "Orders%20of%20Temporary%20Custody", "Parcel", "Parenting%20Education%20Program", "Parole", "Parties",
            "Party", "Paternity", "Pendente%20lite%20order", "Peremptory%20Challenge", "Perjury", "Petition",
            "Petitioner", "Plaintiff", "Plea", "Plea%20Bargain", "Pleadings", "Post%20Judgment", "Posting%20Bond",
            "Practice%20Book", "Pre-Sentence%20Investigation", "Pretrial", "Pretrial%20Hearing", "Pro%20Se",
            "Pro%20se%20Divorce", "Probable%20Cause%20Hearing", "Probate/Probate%20Court", "Probation",
            "Probation%20Absconder", "Promise%20to%20Appear", "Prosecute", "Prosecutor", "Protective%20Order",
            "Public%20Defender", "Ready", "Record", "Referee", "Residential%20Treatment%20Programs",
            "Respondent", "Rest", "Restitution", "Restraining%20Order", "Return%20Date", "Revocation%20Hearing",
            "Rule%20to%20Show%20Cause", "Seal", "Senior%20Judge", "Sentence%20Modification", "Sentence%20Review",
            "Sentences", "Sentencing", "Serious%20Juvenile%20Offender", "Serious%20Juvenile%20Offense", "Service",
            "Short%20Calendar", "Slip%20Opinions", "Small%20Claims", "Special%20Sessions%20of%20the%20Superior%20Court",
            "State%20Referee", "States%20Attorney", "Statute", "Statute%20of%20Limitations", "Stay", "Stipulation",
            "Subpoena", "Subpoena%20Duces%20Tecum", "Substance%20Abuse%20Education", "Substitute%20Charge",
            "Summary%20Process", "Summons", "Support%20Enforcement%20Officer", "Surety%20bond", "Testimony",
            "Time%20Served", "Title", "Tort", "Transcript", "Transfer", "Transfer%20Hearing", "Trial%20De%20Novo",
            "Trial%20Referee", "Uncared%20For", "Unconditional%20Discharge", "Vacate", "Venue",
            "Victim%20Services%20Advocate", "Violation", "Violation%20of%20Probation", "Visitation", "Voir%20Dire",
            "Wage%20Execution", "Wage%20Withholding", "Witness", "Writ", "Youth", "Youthful%20Offender"]


class UserBehavior(TaskSet):

    def on_start(self):
        """ on_start is called when a Locust start before any task is scheduled """
        #self.login()
        pass

    def on_stop(self):
        """ on_stop is called when the TaskSet is stopping """
        #self.logout()
        pass

    ############## Helpers ##############
    def login(self, username, password):
        response = self.client.get("/user/login/")
        csrftoken = response.cookies['csrftoken']
        self.client.post("/user/login/", {"username": username, "password": password},
                         headers={"X-CSRFToken": csrftoken})

    def logout(self):
        self.client.get("/user/logout/")

    def register(self, email, password, first_name, last_name):
        response = self.client.get("/user/register/")
        csrftoken = response.cookies['csrftoken']
        self.client.post("/user/register/",
                         {
                             "email": email,
                             "password1": password,
                             "password2": password,
                             "first_name": first_name,
                             "last_name": last_name,
                             "agreed_to_tos": "on",
                          },
                         headers={"X-CSRFToken": csrftoken})

    def random_endpoint_page(self, api_host, endpoint, depth, parameters):
        parameters = "?" + "&".join(["{}={}".format(param, parameters[param]) for param in parameters])
        response = self.client.get("https://{}/v1/{}/{}".format(api_host, endpoint, parameters))
        json_results = json.loads(response.content.decode())
        result_limit = math.floor(json_results['count'] / 100)
        traversal_limit = result_limit if result_limit < depth else depth
        target_page = choice(range(0, traversal_limit))
        current_page = 0
        while target_page > current_page:
            current_page += 1
            if not json_results['next']:
                break
            response = self.client.get(json_results['next'])
            json_results = json.loads(response.content.decode())

        return json_results


    ############## Tasks ##############

    ### STATIC PAGE AVAILABILITY ###
    @task(10)
    def index(self):
        self.client.get("/{}".format(choice(static_paths)))

    # Log in
    @task(2)
    def profile(self):
        self.login()
        self.client.get("/user/details").content
        self.logout()

    @task(1)
    def ten_individual_cases(self):
        list_page = self.random_endpoint_page(api_host, "cases", 100, {"jurisdiction": choice(["ark", "ill"])})
        counter = 0
        while counter < 10:
            counter += 1
            self.client.get(
                "{}?full_case=true&body_format={}".format(
                    choice(list_page['results'])['url'],
                    choice(["html", "xml", "text"])
                )
            )

    @task(2)
    def scroll_through_full_cases(self):
        parameters = {"jurisdiction": choice(["ark", "ill"]), "full_case": "true"}
        list_page = self.random_endpoint_page(api_host, "cases", 100, parameters)

    @task(8)
    def scroll_through_full_text_search(self):
        parameters = {"search": choice(search_terms)}
        list_page = self.random_endpoint_page(api_host, "cases", 15, parameters)

    @task(10)
    def scroll_random_endpoint(self):
        self.random_endpoint_page(api_host, choice(endpoints), 10000, {})

    @task(3)
    def register_user(self):
        attempts = 0
        registration = False
        while not registration and attempts < 5:
            attempts += 1
            registration = self.register(
                generated_user_email_template.format(randint(100000, 999999), "case", "test"),
                generated_user_password,
                generated_user_first_name,
                generated_user_last_name)

class WebsiteUser(HttpLocust):
    task_set = UserBehavior
    min_wait = 5000
    max_wait = 9000