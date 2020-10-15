{% load static %}
{% load pipeline %}
{% load api_url %}
title: Caselaw Access Project – Tutorial - Beginner's Introduction to APIs
page_image: img/og_image/tools_api.png
meta_description: Caselaw Access Project's absolute beginner's tutorial on using RESTful APIs
explainer: Learn how to query the CAP API using different types of data.

If you're generally familiar with [RESTful]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-restful) 
[APIs]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-api) but would like a gentler introduction 
to our API than our documentation affords, you're in the right place. If you're not comfortable with RESTful APIs and 
would like a generalized introduction to them, many folks consider our 
[Beginner's Introduction to APIs]({% url 'docs' 'tutorials_and_guides/intro_to_apis' %}) to be a useful introduction.
If you've had enough and would prefer to just access the cases using a human-centric interface, please check out our 
[search tool]({% url 'search' %}). 
  
So when you're working with CAPAPI, the same principles apply. Rather than http://www.google.com, you'll be using 
{% api_url "api-root" %}. Rather than using the /search?q= endpoint and parameter, you'll be using one of our 
[endpoints]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-endpoint) and the parameters we've 
defined. Would you like to see how this works in a real application? 
Head over to our [search tool]({% url 'search' %}), click on the 'SHOW API CALL' link below the search button and 
construct a query. The URL box below the search form will update as you change your search terms. You can hover over 
each field in the URL to highlight its counterpart in the search form, or hover over each input box in the search form 
to highlight its counterpart in the URL. When you've constructed the query, click on the API URL to head over to the 
API, or click on the search button to use our search feature.
  
When you perform a query in a web browser using our API, there are some links and buttons, but the data itself is in a 
text-based format with lots of brackets and commas. This format is called JSON, or JavaScript Object Notation. We use 
this format because software developers can easily utilize data in that format in their own programs. We do intend to 
have a more user-friendly case browser at some point soon, but we're not quite there yet. 
  
OK! That about does it for our beginner's introduction to web-based APIs. Please check out our 
[usage examples](#usage-examples") section to see some of the ways you can put these principles to work in CAPAPI. If you have 
any suggestions for making this documentation better, we'd appreciate your taking the time to let us know in an issue 
report in [our repository on github.com](https://github.com/harvard-lil/capstone/issues). 
  
Thanks, and good luck!
