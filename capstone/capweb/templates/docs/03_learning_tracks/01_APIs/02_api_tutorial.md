{% load docs_url %}{% load api_url %}
title: CAP API Tutorial
meta_description: Tutorial on using RESTful APIs to query CAP data
explainer: Learn how to query the CAP API using different types of data.

If you're generally familiar with
[RESTful]({% docs_url 'glossary' %}#def-restful)
[APIs]({% docs_url 'glossary' %}#def-api)
but would like a gentler introduction to our API than our documentation
affords, you're in the right place. If you're not comfortable with
RESTful APIs and would like a generalized introduction to them, try our [Beginner's Introduction to
APIs]({% docs_url 'intro_to_apis' %}). If you've had enough and would prefer just to access the cases
using a human-centric interface, please check out our [search
tool]({% url 'search' %}).

# Intro: Browsable API

Let's query the CAP API using a web browser.

In a separate tab, navigate to <{% api_url "api-root" %}>

    {
        "cases": "{% api_url "cases-list" %}",
        "jurisdictions": "{% api_url "jurisdiction-list" %}",
        "courts": "{% api_url "court-list" %}",
        "volumes": "{% api_url "volumemetadata-list" %}",
        "reporters": "{% api_url "reporter-list" %}",
        "ngrams": "{% api_url "ngrams-list" %}",
        "user_history": "{% api_url "api-root" %}user_history/",
        "citations": "{% api_url "extractedcitation-list" %}"
    }

Congratulations! You just executed your first query to the CAP API! While the results might not be incredibly exciting, 
it's the first step towards doing fantastic work.

You might first notice the unusual, code-ish-looking format of this data. It's called JSON, or JavaScript Object 
Notation, and we'll look into that soon. You probably also recognized some of the terms on the left, such as cases, 
jurisdictions, courts, etc. Each is the name of an API 
[endpoint]({% docs_url 'glossary' %}#def-endpoint), through which you
receive one type of data. For example, to find a court, you might use the `/courts` endpoint. Click on the URL to the
right of "courts."

    {
        "count": 3117,
        "next": "{% api_url "court-list" %}?cursor=cD1BdWJ1cm4rQ2l0eStDb3VydA%3D%3D",
        "previous": null,
        "results": [
            {
                "id": 25221,
                "url": "{% api_url "court-list" %}sc-2/",
                "name": "",
                "name_abbreviation": "S.C.",
                "jurisdiction": "S.C.",
                "jurisdiction_url": "{% api_url "jurisdiction-list" %}sc/",
                "slug": "sc-2"
            },
            {
                "id": 15658,
                "url": "{% api_url "court-list" %}accomack-cty-cir-ct/",
                "name": "Accomack County Circuit Court",
                "name_abbreviation": "Accomack Cty. Cir. Ct.",
                "jurisdiction": "Va.",
                "jurisdiction_url": "{% api_url "jurisdiction-list" %}va/",
                "slug": "accomack-cty-cir-ct"
            },
        […]

Whoa! That's a lot more data! Before we continue, let's take a look at the JSON format.

# Intro to JSON

[JSON, or JavaScript Object Notation](https://en.wikipedia.org/wiki/JSON), is a simple but
flexible way to represent data in text. What people do with this format can be quite complex,
but we won't need to dive too deep to understand the API contents.

Let's start with a bit of simple example data in the form of a shopping list to get us started.

* Grocery Store:
    * 3 apples
    * 1 galangal knob
    * 7 cans of SPAM
    * 1 gallon apple cider
* Hardware Store:
    * 1 finishing nail
    * 1 small bag of 20oz hammers

JSON has several ways to store individual pieces of data:

* a string, e.g. "apple" (which is always in double-quotes)
* a number, e.g. 7
* true/false
* *null* (essentially an explicit way of saying "there is no value.")

JSON has several ways to store multiple pieces of data:

* an array, a simple list of any of these things, e.g. ["apple", "can of spam", "apple cider"]
* an object, a type of list in which each thing in the list has a label, e.g. {"name": "CAP'n Crunch", "rank": "Admiral"}

This is all simpler than it might initially sound. For example, one of the more straightforward ways we could store our 
grocery list above is by using an array.

    [ "apple",
     "apple",
     "apple",
     "galangal knob",
     "can of SPAM",
     "can of SPAM",
     "can of SPAM",
     "can of SPAM",
     "pouch of SPAM",
     "pouch of SPAM",
     "pouch of SPAM",
     "gallon apple cider",
     "small bag of 20oz hammers",
     "finishing nail" ]

Pretty simple but pretty inefficient. We can make it more efficient by using objects. We'll make the name of each 
grocery item the label of the item element, and then we'll make the value of each element the quantity.

    {
      "apple": 3,
      "galangal knob": 1,
      "can of SPAM": 4,
      "pouch of SPAM": 3,
      "gallon apple cider": 1,
      "small bag of 20oz hammers": 1,
      "finishing nail": 1 
    }

Wow, that's a lot more efficient, but it sure would be nice to see the store to locate each item.

    {
          "apple": {
            "store": "grocery",
            "quantity": 3
          },
          "galangal knob": {
            "store": "grocery",
            "quantity": 1
          },
          "can of SPAM": {
            "store": "grocery",
            "quantity": 4
          },
          "pouch of SPAM":{
            "store": "grocery",
            "quantity": 3
          },
          "gallon apple cider":{
            "store": "grocery",
            "quantity": 1
          },
          "small bag of 20oz hammers": {
            "store": "hardware",
            "quantity": 1
          },
          "finishing nail": {
            "store": "hardware",
            "quantity": 1
          },
        }
    }

Oof, that's even bulkier than the list. Let's add some hierarchy. Within the base JSON object, we'll have two 
objects — one for each store. Then, within each store, we'll have each of the items we want to purchase at that store.

    {
      "grocery": {
        "apple": {
          "quantity": 3
        },
        "galangal knob": {
          "quantity": 1
        },
        "can of SPAM": {
          "quantity": 4
        },
        "pouch of SPAM":{
          "quantity": 3
        },
        "gallon apple cider":{
          "quantity": 1
        }
      },
      "hardware": {
        "small bag of 20oz hammers": {
          "quantity": 1
        },
        "finishing nail": {
          "quantity": 1
        },
      }
    }

It is getting better! We could optimize that SPAM entry, though--- let's change our structure so it can handle variety.

    {
      "grocery": {
        "apple": {
          "quantity": 3
        },
        "galangal knob": {
          "quantity": 1
        },
        "SPAM":{
          "pouch": 3,
          "can": 4
        },
        "gallon apple cider":{
          "quantity": 1
        }
      },
      "hardware": {
        "small bag of 20oz hammers": {
          "quantity": 1
        },
        "finishing nail": {
          "quantity": 1
        },
      }
    }

Great. We've converted our human-readable grocery list into a data structure easily usable by both humans and computers.
So how can you use this data in your environment? Almost all modern programming languages and data tools support 
ingesting data in JSON. Consult your environment's documentation for info on how to ingest and access JSON data.

# curl

In practice, people rarely use web browsers to perform this work. Copying and pasting all of that data is hugely 
inefficient and doesn't allow a computer program to take in data, process it, and request new, dynamic data as a result.
 Let's look at the most commonly used option, which doesn't require any programming knowledge: curl.

From your computer's command line or terminal, curl can download the data from any URL and display it on a screen or 
save it to a file. Help to install curl on your system is a quick google search away. Many systems, such as Linux and 
macOS, have curl preinstalled.

    $ curl {% api_url "api-root" %}
    {"cases":"{% api_url "api-root" %}","jurisdictions":"{% api_url "jurisdiction-list" %}","courts":"{% api_url "court-list" %}","volumes":"{% api_url "volumemetadata-list" %}","reporters":"{% api_url "reporter-list" %}","ngrams":"{% api_url "ngrams-list" %}","user_history":"{% api_url "api-root" %}user_history/","citations":"{% api_url "extractedcitation-list" %}"}

<small>[Browsable API Link]({% api_url "api-root" %})</small>

Hmm... that's not very readable. On macOS and Linux, we can format the output using the json_pp utility:

    curl {% api_url "api-root" %} | json_pp
    {
       "reporters" : "{% api_url "reporter-list" %}",
       "courts" : "{% api_url "court-list" %}",
       "jurisdictions" : "{% api_url "jurisdiction-list" %}",
       "ngrams" : "{% api_url "ngrams-list" %}",
       "user_history" : "{% api_url "api-root" %}user_history/",
       "citations" : "{% api_url "extractedcitation-list" %}",
       "volumes" : "{% api_url "volumemetadata-list" %}",
       "cases" : "{% api_url "cases-list" %}"
    }
<small>[Browsable API Link]({% api_url "api-root" %})</small>

Now that's more like it. We can also save the output to a JSON file:

    curl {% api_url "api-root" %} | json_pp > test_output.json

Now we have a file called test_output.json, which contains the JSON of our query. The Windows process is similar, but 
not all of the utilities come preinstalled, and a walkthrough of that process is out of this tutorial's scope. 
Fortunately, querying and saving JSON data is a fairly common task, and you should be able to find a fair amount of 
information about doing so on the internet.

# Overview of the endpoints

Let's take a look at the output of our example command:

    curl {% api_url "api-root" %} | json_pp
    {
        "cases": "{% api_url "cases-list" %}",
        "jurisdictions": "{% api_url "jurisdiction-list" %}",
        "courts": "{% api_url "court-list" %}",
        "volumes": "{% api_url "volumemetadata-list" %}",
        "reporters": "{% api_url "reporter-list" %}",
        "ngrams": "{% api_url "ngrams-list" %}",
        "user_history": "{% api_url "api-root" %}user_history/",
        "citations": "{% api_url "extractedcitation-list" %}"
    }
<small>[Browsable API Link]({% api_url "api-root" %})</small>

We see a JSON object with cases, jurisdictions, courts, volumes, reporters, ngrams, user_history, and citations. If 
you're familiar with legal texts, most of those terms probably look familiar to you. 
Other names, such as ngrams and user_history, aren't standard legal terms. You can 
get a description of endpoints, their arguments, and their output in the 
[API Reference]({% docs_url 'api' %}). Let's start with a simple query to the base 
courts endpoint.

    curl {% api_url "court-list" %}
    {
       "previous" : null,
       "next" : "{% api_url "court-list" %}?cursor=cD1BdWJ1cm4rQ2l0eStDb3VydA%3D%3D",
       "count" : 3117,
       "results" : [
          {
             "jurisdiction_url" : "{% api_url "jurisdiction-list" %}sc/",
             "id" : 25221,
             "jurisdiction" : "S.C.",
             "slug" : "sc-2",
             "name_abbreviation" : "S.C.",
             "name" : "",
             "url" : "{% api_url "court-list" %}sc-2/"
          },
          {
             "url" : "{% api_url "court-list" %}accomack-cty-cir-ct/",
             "jurisdiction" : "Va.",
             "slug" : "accomack-cty-cir-ct",
             "name_abbreviation" : "Accomack Cty. Cir. Ct.",
             "jurisdiction_url" : "{% api_url "jurisdiction-list" %}va/",
             "id" : 15658,
             "name" : "Accomack County Circuit Court"
          },
          [...]
          
<small>[Browsable API Link]({% api_url "court-list" %} )</small>
         

Wow, that's a lot of stuff! Scroll up to the top of the output, and let's take a look at the first 
three arguments, but in reverse order:

Count: 3117

This shows the number of results returned by your query. Since we didn't add any filters or other parameters to our 
query, this number tells us that our API contains 3,117 court entries.

Next: (a URL)

Since any given query could return thousands of results, for the sake of server performance, we can serve 100 per 
request, maximum. This URL is where we would go to fetch the next 100 results. Breaking it down a bit further, we can 
see that the base URL is the same, but now there's the cursor parameter, which is generated by the server, and specific 
to your results set. 

Previous: null

Previous does the same thing as Next but helps us find our way back instead of forward. Since we're on the first "page" 
of results here, this value is null.

Let's see how this looks with some live queries.

# Dig-in With Real Queries

This is a simple query to the jurisdictions endpoint. There are no
[parameters]({% docs_url 'glossary' %}#def-parameter) to this query, which
is where we would have submitted any query filters, so it should return all jurisdictions.

Either execute it with curl or visit the URL in your browser to see the output.

    curl {% api_url "jurisdiction-list" %}

    {
        "count": 63,
        "next": null,
        "previous": null,
        "results": [
            {
                "url": "<{% api_url "jurisdiction-list" %}ala/>",
                "id": 23,
        [...]
<small>[Browsable API Link]({% api_url "jurisdiction-list" %})</small>

This returns a complete list of jurisdictions in our data set. While having a list of all jurisdictions could be useful 
in some circumstances, let's refine the query to see which of these jurisdictions is 
[open]({% docs_url 'glossary' %}#def-open). We can accomplish
this by adding a filter argument saying the "whitelisted" field should be *true*. (again, you can get a full list of 
arguments and their possible values in the [API Reference]({% docs_url 'api' %}).)

    curl <{% api_url "jurisdiction-list" %}?whitelisted=true>

    {
        "count": 4,
        "next": null,
        "previous": null,
        "results": [
            {
                "url": "{% api_url "jurisdiction-list" %}ark/",
                "id": 34,
                "slug": "ark",
                "name": "Ark.",
                "name_long": "Arkansas",
                "whitelisted": true
            },
            {
                "url": "{% api_url "jurisdiction-list" %}ill/",
                "id": 29,
                "slug": "ill",
                "name": "Ill.",
                "name_long": "Illinois",
                "whitelisted": true
            },
            {
                "url": "{% api_url "jurisdiction-list" %}nc/",
                "id": 5,
                "slug": "nc",
                "name": "N.C.",
                "name_long": "North Carolina",
                "whitelisted": true
            },
            {
                "url": "{% api_url "jurisdiction-list" %}nm/",
                "id": 52,
                "slug": "nm",
                "name": "N.M.",
                "name_long": "New Mexico",
                "whitelisted": true
            }
        ]
    }
<small>[Browsable API Link]({% api_url "jurisdiction-list" %}?whitelisted=true)</small>

Well, that narrowed it down a bit. While this is certainly a manageable list, let's refine it again using an additional 
filter parameter for the heck of it.

    curl {% api_url "jurisdiction-list" %}?name=N.C.&whitelisted=true

    {
        "count": 1,
        "next": null,
        "previous": null,
        "results": [
            {
                "url": "{% api_url "jurisdiction-list" %}nc/",
                "id": 5,
                "slug": "nc",
                "name": "N.C.",
                "name_long": "North Carolina",
                "whitelisted": true
            }
        ]
    }
<small>[Browsable API Link]({% api_url "jurisdiction-list" %}?name=N.C.&whitelisted=true)</small>

Ok, well now we've got one result. What can we do with it? Let's see which reporter series are available for that 
jurisdiction by heading on over to the reporters endpoint, and using this jurisdiction slug as a filter:

    curl {% api_url "reporter-list" %}?jurisdictions=nc

    {
        "count": 2,
        "next": null,
        "previous": null,
        "results": [
            {
                "id": 365,
                "url": "{% api_url "reporter-list" %}365/",
                "full_name": "North Carolina Court of Appeals Reports",
                "short_name": "N.C. App.",
                "start_year": 1963,
                "end_year": 2014,
                "jurisdictions": [
                    {
                        "url": "{% api_url "jurisdiction-list" %}nc/",
                        "id": 5,
                        "slug": "nc",
                        "name": "N.C.",
                        "name_long": "North Carolina",
                        "whitelisted": true
                    }
                ],
                "frontend_url": "https://cite.case.law/nc-app/"
            },
            {
                "id": 549,
                "url": "{% api_url "reporter-list" %}549/",
                "full_name": "North Carolina Reports",
                "short_name": "N.C.",
                "start_year": 1778,
                "end_year": 2017,
                "jurisdictions": [
                    {
                        "url": "{% api_url "jurisdiction-list" %}nc/",
                        "id": 5,
                        "slug": "nc",
                        "name": "N.C.",
                        "name_long": "North Carolina",
                        "whitelisted": true
                    }
                ],
                "frontend_url": "https://cite.case.law/nc/"
            }
        ]
    }
<small>[Browsable API Link]({% api_url "reporter-list" %}?jurisdictions=nc)</small>

Ok, great — 2 reporters. Let's choose one, "N.C. App.", and head over to the cases endpoint. If we look at the cases 
endpoint in the [API Reference]({% docs_url 'api' %}), we can see that the reporter 
filter parameter takes a reporter id as the argument.

    curl {% api_url "cases-list" %}?reporter=365

    {
        "count": 26755,
        "next": "{% api_url "cases-list" %}?cursor=eyJwIjogWzAuMCwgIjE5NjgtMDYtMTIiLCA4NTUzMzgyXX0%3D&reporter=365",
        "previous": null,
        "results": [
            {
                "id": 8555137,
        [...]

<small>[Browsable API Link]({% api_url "cases-list" %}?reporter=365)</small>

Let's refine those cases to get only cases decided in 2000. We can use the decision_date__gte and decision_date__lte 
parameters for that!

    curl {% api_url "cases-list" %}?reporter=365&decision_date__gte=2000&decision_date__lte=2001

    {
        "count": 514,
        "next": "{% api_url "cases-list" %}?cursor=eyJwIjogWzAuMCwgIjIwMDAtMDMtMjEiLCAxMTA5MjQyNV19&decision_date__gte=2000&decision_date__lte=2001&reporter=365",
        "previous": null,
        "results": [
            {
                "id": 11239345,
        [...]

<small>[Browsable API Link]({% api_url "cases-list" %}?reporter=365&decision_date__gte=2000&decision_date__lte=2001)</small>

And now let's find cases that only mention fraud in their text.

    curl {% api_url "cases-list" %}?search=fraud&reporter=365&decision_date__gte=2000&decision_date__lte=2001

    {
        "count": 50,
        "next": null,
        "previous": null,
        "results": [
            {
                "id": 9497365,
        [...]
        
<small>[Browsable API Link]({% api_url "cases-list" %}?search=fraud&reporter=365&decision_date__gte=2000&decision_date__lte=2001)</small>
            
Great. Now let's get all of the case texts associated with each of those cases, using the full_case parameter.


    curl {% api_url "cases-list" %}?search=fraud&reporter=365&decision_date__gte=2000&decision_date__lte=2001&full_case=true
    
    {
        "count": 50,
        "next": null,
        "previous": null,
        "results": [
            {
                "id": 9497365,
                [...]
                 "casebody": {
                        "status": "ok",
                        "data": {
                            "head_matter": "THE JAY GROUP, LTD.[...]
<small>[Browsable API Link]({% api_url "cases-list" %}?search=fraud&reporter=365&decision_date__gte=2000&decision_date__lte=2001&full_case=true)</small>

There you have it. We've walked through different endpoints in the API to narrow down our search to get a pretty 
specific set of cases, with their full case text.

# Next Steps

Would you like to see how this works in a real application? Head over to our 
[search tool]({% url 'search' %}), construct a query, and click on the 'SHOW API CALL' link below the search button. 
The URL box below the search form will update as you change your search terms. You can hover over each field in 
the URL to highlight its counterpart in the search form or hover over each input box in the search form to highlight 
its counterpart in the URL. When you've constructed the query, click on the API URL to head over to the API, or click 
on the search button to use our search feature. 

Also, check out our gallery to see how researchers, developers, and other folks have used CAP data. 
We're continually amazed by the ways people put this data to work.

If you'd like to dig in and get your hands dirty, the API user guide is where you want to go. It gives you everything 
you need to make the most out of our data. If you think your use case might be better served by downloading large 
amounts of data and working with it locally, check out our Bulk Data. 

# Wrap-up

OK! That about does it for our beginner's introduction to web-based APIs.
If you want more, head on to our [In-Depth Tutorial]({% docs_url 'in_depth' %}).

Thanks, and good luck!
