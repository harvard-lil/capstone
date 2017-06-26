from django.test import TransactionTestCase
from rest_framework.test import RequestsClient
from bs4 import BeautifulSoup

from capi_project.tests import helpers
from capi_project import models

class AccountTestCase(TransactionTestCase):
    def setUp(self):
        helpers.setup_authenticated_user(email="authentic_boblawblaw@lawblog.com", first_name="Authentic-Bob",
                                                last_name="Lawblaw", password="unique_authentic_password")
    def test_register_view(self):
        client = RequestsClient()
        response = client.get("http://testserver/accounts/register")
        assert response.status_code == 200

        soup = BeautifulSoup(response.content, 'html.parser')
        inputs = soup.select("input")
        input_names = map(lambda x: x['name'], inputs)
        assert "csrfmiddlewaretoken" in input_names
        assert "email" in input_names
        assert "password" in input_names


    def test_login_view(self):
        client = RequestsClient()
        response = client.get("http://testserver/accounts/login")
        assert response.status_code == 200

        soup = BeautifulSoup(response.content, 'html.parser')
        inputs = soup.select("input")
        input_names = map(lambda x: x['name'], inputs)
        assert "csrfmiddlewaretoken" in input_names
        assert "email" in input_names
        assert "password" in input_names


    def test_login(self):
        client = RequestsClient()
        response = client.get("http://testserver/accounts/login")
        csrftoken = response.cookies['csrftoken']
        user = models.CaseUser.objects.get(email="authentic_boblawblaw@lawblog.com")
        user_password = "unique_authentic_password"

        """
        Testing valid login 
        """
        response = client.post("http://testserver/accounts/view_details/",
                               json={'email': user.email, 'password': user_password},
                               headers={'X-CSRFToken': csrftoken})
        assert response.status_code == 200

        soup = BeautifulSoup(response.content, 'html.parser')
        api_key = soup.findAll("span", {"class": "user_api_key"})[0].text

        assert api_key == models.Token.objects.get(user=user).key

        case_allowance = soup.findAll("span", {"class": "user_case_allowance"})[0].text
        assert case_allowance == "500"


        """
        Testing invalid login 
        """
        response = client.post("http://testserver/accounts/view_details/",
                               json={'email': user.email, 'password': user_password + "1"},
                               headers={'X-CSRFToken': csrftoken})
        assert response.status_code == 400
