{% load static %}
{% load pipeline %}
{% load api_url %}
title: Caselaw Access Project – Tutorial - API Keys
page_image: img/og_image/tools_api.png
meta_description: Caselaw Access Project tutorial to learn how to use our API Keys.
explainer: Learn how to get access to 500 access-throttled cases per day with a free API key.

You may access much of the data in our API without an account. For example, all case metadata is available without any restrictions. However, in most jurisdictions, we are contractually obligated to limit users without unthrottled research accounts to 500 full-text cases per day. 

Check out which jurisdictions are whitelisted— ones you may download in their entirety with no account or throttling— 
and see the daily limits of our non-whitelisted case text in our 
[access limits documentation.]({% url 'docs' 'api/api' %}#access-limits)

# How to Create an Account {: class="subtitle" }
To keep track of how many case texts each user has downloaded that day, we require an account. To create an account:
Click on the [LOG IN](https://case.law/user/login/) link at the top of the screen.
Click on the [sign up](https://case.law/user/register/) link below the login form.
Fill in each field and click the blue "REGISTER" button.
You will receive an email from our registration system— your account is not active until you click the link in that email. 
HOW TO AUTHENTICATE WHILE USING OUR WEBSITE
When using our website or using our API in your web browser, log in with the LOG IN link at the top of the screen. Doing so will authenticate any [request]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-request) you make through your web browser.



## Find your API Key {: class="subtitle" }

First, log in to your account using the[LOG IN](https://case.law/user/login/) link at the top of the screen.
After you've signed in, the LOG IN link at the top of the screen now reads [ACCOUNT](https://case.law/user/details). Click that link.
In the API key field, you should see a 40 [character]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-character) long [string]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-string). That is your API key.
HOW TO INCLUDE YOUR API KEY IN YOUR REQUEST
You must submit the API key in the request headers. The headers are a group of metadata fields automatically included in the background of each request. Your browser (or equivalent like `curl`, or a requests library) uses headers to describe each request to the server, and the server to describe its response. For example, your web browser will include a header field called `User-Agent`, which tells the web server what version of what browser you're using, on what operating system. Among the various headers in its response, the server will include a `Content-Type` field, which says if it's HTML text, an image, etc.


## How to Authenticate While Using Our API {: class="subtitle" }
Authenticating your API requests involves submitting your API Key as part of your request. 

Our service requires you to include the header labeled `Authorization`, containing the string `Token [your API key]`. So, if your API key were `1234thisisntarealapikeysodontusethisone1`, your header would look like this: `Authorization: Token 1234thisisntarealapikeysodontusethisone1`. 

In practice, that looks like this:
### curl {: class="subtitle" }
	curl -H "Authorization: Token abcd12345" "https://api.case.law/v1/cases/435800/?full_case=true"

### python requests library {: class="subtitle" }
	response = requests.get(
    'https://api.case.law/v1/cases/435800/?full_case=true',
    headers={'Authorization': 'Token abcd12345'}
)

### web browser {: class="subtitle" }
As long as you've logged in through the website, there's no need to do anything special. Your browser handles it automatically in the background.

