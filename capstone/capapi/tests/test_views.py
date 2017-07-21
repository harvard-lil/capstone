from django.test import TransactionTestCase
from django.http.request import QueryDict, MultiValueDict
from rest_framework.test import RequestsClient
from bs4 import BeautifulSoup

from capapi.tests import helpers
from capapi import models, view_helpers

class AccountViewsTestCase(TransactionTestCase):
    def setUp(self):
        helpers.setup_authenticated_user(email="authentic_boblawblaw@lawblog.com", first_name="Authentic-Bob",
                                                last_name="Lawblaw", password="unique_authentic_password")
    def test_register_view(self):
        client = RequestsClient()
        response = client.get("http://testserver/accounts/register")
        assert response.status_code == 200

        soup = BeautifulSoup(response.content, 'html.parser')
        inputs = soup.select("input")
        input_names = [x['name'] for x in inputs]
        assert "csrfmiddlewaretoken" in input_names
        assert "email" in input_names
        assert "password" in input_names

    def test_login_view(self):
        client = RequestsClient()
        response = client.get("http://testserver/accounts/login")
        assert response.status_code == 200

        soup = BeautifulSoup(response.content, 'html.parser')
        inputs = soup.select("input")
        input_names = [x['name'] for x in inputs]
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


    def test_view_helpers(self):
        dictionary = {'max': ['3'], 'type': ['download'], 'jurisdiction_name': ['alabama']}
        query_params = QueryDict('', mutable=True)
        query_params.update(MultiValueDict(dictionary))
        formatted_params = view_helpers.format_query(query_params, dict())
        """
        assert type is removed
        """
        assert 'type' not in formatted_params
        assert 'max' not in formatted_params

        queries = list(map(view_helpers.make_query, list(formatted_params.items())))
        assert len(queries) == 1

        first_q = queries[0]
        assert first_q.children[0][0] == 'jurisdiction__name__icontains'




