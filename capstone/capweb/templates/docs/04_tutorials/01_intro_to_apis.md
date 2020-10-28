{% load static %}
{% load pipeline %}
{% load api_url %}
title: Caselaw Access Project – Tutorial - Beginner's Introduction to APIs
page_image: img/og_image/docs.png
meta_description: Caselaw Access Project's absolute beginner's tutorial on using RESTful APIs
explainer: This is our absolute beginner's tutorial on using RESTful APIs. Though we are primarily interested in education future CAP users, this knowlege is not CAP-specific; it can be applied to many other APIs.

Are you a little lost in all the technical jargon, but still want to give the API a shot? This is a good place to start!
This is by no means a complete introduction to using 
[APIs]({% url 'docs' 'user_guides/documentation_glossary' %}#def-api), but it might be just enough to 
help situate a technically inclined person who's a bit outside of their comfort zone. If you've had enough and would 
prefer to just access the cases using a human-centric interface, please check out our [search tool]({% url 'search' %}). 
  
Fundamentally, an API is no different from a regular website: A program on your computer, such as a web browser or 
[curl]({% url 'docs' 'user_guides/documentation_glossary' %}#def-curl) sends a bit of data to 
a [server]({% url 'docs' 'user_guides/documentation_glossary' %}#def-server), the server processes that 
data, and then sends a response. If you know how to read a 
[url]({% url 'docs' 'user_guides/documentation_glossary' %}#def-url), you can interact with web-based 
services in ways that aren't limited to clicking on the links and buttons on the screen. 
  
Consider the following [url]({% url 'docs' 'user_guides/documentation_glossary' %}#def-url), which will 
[perform a google search for the word "CAP."](https://www.google.com/search?q=CAP")
  
    https://www.google.com/search?q=CAP
  
Let's break it down into its individual parts:
  
    https://
  
This first part tells your web browser which protocol to use: this isn't very important for our purposes, so we'll 
ignore it.
  
    www.google.com
  
The next part is a list of words, separated by periods, between the initial double-slash, and before the subsequent 
single slash. Many people generically refer to this as the domain, which is only partly true, but the reason why that's 
not entirely true isn't really important for our purposes; the important consideration here is that it points to a 
specific [server]({% url 'docs' 'user_guides/documentation_glossary' %}#def-server), which is just 
another computer on the internet. 

    /search
  
The next section, which is comprised of everything between the slash after the server name and the question mark, is 
called the [path]({% url 'docs' 'user_guides/documentation_glossary' %}#def-path). It's called a path 
because, in the earlier days of the web, it was a 'path' through folders/directories to find a specific file on the web 
server. These days, it's more likely that the path will point to a specific 
[endpoint]({% url 'docs' 'user_guides/documentation_glossary' %}#def-endpoint).
  
  
You can think of an endpoint as a distinct part of a program, which could require specific inputs, and/or provide 
different results. For example, the "login" endpoint on a website might accept a valid username and a password for 
input, and return a message that you've successfully logged in. A "register" endpoint might accept various bits of 
identifying information, and return a screen that says your account was successfully registered.
  
  
Though there is only one part of this particular path, `search`, developers usually organize paths into hierarchical 
lists separated by slashes. Hypothetically, if the developers at Google decided that one generalized search endpoint 
wasn't sufficiently serving people who wanted to search for books or locations, they could implement more specific 
endpoints such as `/search/books` and `/search/locations`.
  
    ?q=CAP
  
The final section of the URL is where you'll find the 
[parameters]({% url 'docs' 'user_guides/documentation_glossary' %}#def-parameter), and is comprised of 
everything after the question mark. Parameters are a way of passing individual, labelled pieces of information to the 
endpoint to help it perform its job. In this case, the parameter tells the `/search` endpoint what to search for. 
Without this parameter, the response wouldn't be particularly useful.
  
A URL can contain many parameters, separated by ampersands, but in this instance, there is only one parameter: the 
rather cryptically named "q," which is short for "query," which has a value of "CAP." Parameter names are arbitrary— 
Google's developers could just as easily have set the parameter name to `?query=CAP`, but decided that "q" would 
sufficiently communicate its purpose. 
  
The Google developers designed their web search endpoint to accept other parameters, too. For example, there is an even 
more cryptically named parameter, 'tbs' which will limit the age of the documents returned in the search results. The 
parameters `?q=CAP&tbs=qdr:y` will perform a web search for "CAP" and limit the results to documents less than a year 
old. 
  
OK! That about does it for our beginner's introduction to web-based APIs.

You can apply all of these principles to the [Caslaw Access Project API]({% api_url "api-root" %}). To find out how, 
check out our [API tutorial]({% url 'docs' 'tutorials/api_tutorial' %}). Or, if you're feeling confident enough, jump right into 
out our [API User Guide]({% url 'docs' 'user_guides/api' %}) and get to work.

If you have any suggestions for making this documentation better, we'd appreciate your taking the time to let us know in
an issue report in [our repository on github.com](https://github.com/harvard-lil/capstone/issues). 
  
Thanks, and good luck!
