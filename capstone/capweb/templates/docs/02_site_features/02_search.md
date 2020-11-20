{% load docs_url %}
title: Search
explainer: The Caselaw Access Project Search Interface searches all official US court cases published in books from 1658 to 2018. The collection includes over six million cases scanned from the Harvard Law School Library shelves. <a href="{% url "about" %}">Learn more about the project.</a>
# Overview

[Search Cap]({% url "search" %}){: class="btn-primary" }

The CAP search tool offers a basic interface for locating and viewing the cases in our
repository. You can use it to search through our cases and some of our metadata
tables, but there are no advanced tools. If you have any feature suggestions, [let us know]({% url 'contact' %}). 
If you're a developer, you might be more interested in directly accessing our
[API]({% docs_url "api" %}) or [Bulk Data]({% docs_url "bulk" %}).

# What's included?

See our [About page]({% url 'about' %}#what-data-do-we-have) for more details on the materials included.

# Searching in CAP is simple

* **First**: Choose What To Search
* **Second**: Select Your Search Criteria
* **Third**: Execute the Search

## First: Choose What To Search

The search tool is set to search cases by default, but it can also search courts, jurisdictions, and reporters. 
To search for something else, use the dropdown menu to the right of the word 'Find.'

## Second: Select Your Search Criteria

Within type of search, there are several fields you can use to define your search. You could search for
cases by their citation or by full-text search, and you can search for reporters by their jurisdiction. You can
even precisely refine your search by using several fields at once. To add a field to your search, simply click
the *Add Field* button, select the field you wish to add from the dropdown, add your search criteria, and press the
search button.

For example, if you were searching our Reporters, the default search field is Jurisdiction. Perhaps you'd like
to search for reporters' names that start with a specific word: Press the *Add Field* button, and from the dropdown
box, and select *Full Name.* There is no need to remove any field boxes you don't plan on entering search terms
into — they will not affect the search results.

## Third: Execute the Search

Here's the easy part — just click on the Search button. The loading screen should pop up momentarily, and your
search results should appear below. If there was a problem contacting the search server, or the server returned
an error with one of your search fields, it appears on-screen.


# Full-Text Case Search

When searching cases, the default search field is "Full-Text Search." This provides some functionality that isn't
available in other search fields. 

## Phrase Search

To search our corpus for the phrase "a pox on both your houses", simply enclose it in double quotes:

```"A pox on both your houses"```

## Exclusion

You can also exclude terms from your search by prepending them with a minus sign. For example, if you wanted to
search for all cases containing the phrase "insurance fraud" but wanted to exclude the word automobile, type:

```"insurance fraud" -automobile```

# Tips

* You may use as many search field boxes as you like.
* Results in metadata searches allow you to efficiently perform a new search for all of the cases related to that result.
For example, if you're searching our jurisdiction list, each result on that list has a "See Cases" button that starts a
new search for all of the cases under the specified jurisdiction. You can get back to your original search
using the back button.
* To share a search, simply copy the URL and pass it along! It will link the user to the specific page of
results you're viewing. To send them to the first page of results, navigate to the first page of results
before copying the URL.

# Getting Legal Help

Our caselaw search tool does not have any cases published after mid-2018, and contains many OCR mistakes.
It is not intended for use in legal proceedings, and we cannot provide individual assistance with legal
research.

To find an attorney, get help with legal research skills, or find up-to-date databases for use in legal proceedings,
please see the [Getting Legal Help]({% url "about" %}#getting-legal-help) section of our About page.
