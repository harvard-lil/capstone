{% load pipeline %}
{% load api_url %}
title: CAP Search
explainer: The Caselaw Access Project Search Interface facilitates searching and viewing all official US court cases published in books from 1658 to 2018. The collection includes over six million cases scanned from the Harvard Law Library shelves. <a href="{% url "about" %}">Learn more about the project.</a>
meta_description: Caselaw Access Project Search Docs
top_section_style: bg-black
row_style: bg-tan

{% block extra_head %} {% stylesheet 'tools' %} {% stylesheet 'docs' %} {% endblock %}

# Overview {: class="subtitle" }

[Search Cap]({% url "search" %}) {: class="btn-primary" }

With this tool, we aim to provide a simple interface for locating and viewing the cases and metadata in the CAP
repository. Right now, this tool is fairly basic. You can use it to search through our cases and some of our metadata
tables, but there are no advanced tools. If you have any feature suggestions, we'd appreciate your taking the time to
let us know either in an issue report in our [Github repo](https://github.com/harvard-lil/capstone/issues), or through
our [contact page[({% url 'contact' %}). If you're a developer, you might be more interested in directly accessing our
[API]({% url "api" %}) [Bulk Data]({% url "bulk-docs" %}).

  {# ==============> SCOPE <============== #}
# What's included? {: class="subtitle" }

The CAP search tool searches everything included in the [API]({% url 'api' %}). See our
[About page]({% url 'about' %}#data) for more details on the materials included.

# Searching in CAP is simple {: class="subtitle" }

* **First:** Choose What To Search
* **Second:** Select Your Search Criteria
* **Third:** Execute the Search

## Choose What To Search
The search tool allows you to search through several different tables of objects; right now, you may search cases,
courts, jurisdictions, and reporters. When you first arrive at the search page, it is set to search cases. To search for
something else, click on "Cases" and select something else from the dropdown menu. By default, the search tool is set to
search for Cases. To search for something else, click on "Cases" and select something from the dropdown menu.

For example, you may want to search our jurisdiction list. At the top of the search form where it says "Search for
__Cases__" (or whatever else it might be set to) you should click on the word "Cases" and select something else from the
dropdown menu.

## Select Your Search Criteria

Within each table of objects, there are several fields you can use to define your search. You could search for
cases by their citation or by full-text search, and you can search for reporters by their jurisdiction. You can
even precisely refine your search by using several fields at once. To add a field to your search, simply click
the "Add Field" button, select the field you wish to add from the dropdown, add your search criteria, and press the
search button.

For example, if you were searching our Reporters, the default search field is Jurisdiction. Perhaps you'd like
to search for reporters' names that start with a specific word: Press the "Add Field" button, and from the dropdown
box, and select "Full Name." There is no need to remove any field boxes you don't plan on entering search terms
into— they will not affect the search results— but it certainly might make complex searches easier to manage,
visually.

## Execute the Search

Here's the easy part— just click on the Search button. The loading screen should pop up momentarily, and your
search results should appear below. If there was a problem contacting the search server, or the server returned
an error with one of your search fields, it appears on-screen.

# Tips {: class="subtitle" }
You may use as many search field boxes as you like.

For Full-Text searching (currently only available in Cases) each separate word is treated as a separate search term
bound with a logical "and." We don't yet offer phrase searching but plan to implement it soon.

Results in metadata searches allow you to efficiently perform a new search for all of the cases related to that result.
For example, if you're searching our jurisdiction list, each result on that list has a "See Cases" button that starts a
new search for all of the cases under the specified jurisdiction. Don't worry— you can get back to your original search
using the back button.

You may use as many search field boxes as you like.

To share a search, simply copy the URL and pass it along! It will link the user to the specific page of
results you're viewing. To send them to the first page of results, navigate to the first page of results
before copying the URL.

# Getting Legal Help {: class="subtitle" }

Our caselaw search tool is not kept up to date. It currently has caselaw through mid-2018, but may contain many mistakes
as well. It is not intended for use in legal proceedings, and we cannot provide individual assistance with legal
research.

To find an attorney, get help with legal research skills, or find up-to-date databases for use in legal proceedings,
please see the [Getting Legal Help]({% url "about" %}#legal-help) section of our About page.

