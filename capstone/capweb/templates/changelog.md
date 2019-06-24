{% load static %}
{% load pipeline %}
{% load api_url %}
title: Changelog
page_image: 'img/og_image/tools.png'
meta_description: CAP Data/Feature Change Log
explainer: If our data or user-facing research features change in significant ways&mdash; beyond bug fixes and minor changes&mdash; we'll record those changes here.
top_section_style: bg-black
row_style: bg-tan
extra_head: {% stylesheet 'docs' %}

# API {: class="subtitle" }

* **June 19, 2019**{: class='list-header' }
{: add_list_class="bullets" }
    * We added the [ngrams]({% api_url "ngrams-list" %}) endpoint to our API. Here are the
    [docs]({% url 'api' %}#endpoint-ngrams).


# Website {: class="subtitle" }

* **June 19, 2019**{: class='list-header' }
{: add_list_class="bullets" }
    * We started recording this public changelog.
    * We added the [historic trends]({% url 'trends' %}) tool to our website.

<!--
# Data {: class="subtitle" }

The spacing and placement of all the elements in the list is critical.

Make subsequent entries bump up right against the initial list, like this:

* **June 20, 2019**{: class='list-header' }
{: add_list_class="bullets" }
    * Added API endpoint to give away free money.
    * Documentation to come soon.
* **June 19, 2019**{: class='list-header' }
{: add_list_class="bullets" }
    * We added a new endpoint to our API: `ngrams`.
    * Documentation to come soon.


To add a new section, just add another headline with {: class="subtitle" }... there must be exactly one
space in between the curly brace and the last letter of the headline: like this:

# Bulk Data {: class="subtitle" }
-->
