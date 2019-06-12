{% load static %}
{% load api_url %}
title: Tools
meta_description: Tools for accessing caselaw
{% spaceless %}
{% if ngrams %}
explainer: The capstone of the Caselaw Access Project is a robust set of tools which facilitate access to the cases
    and their associated metadata. We currently offer five ways to access the data:
    <a href="{% api_url "api-root" %}">API</a>, <a href="{% url "bulk-download" %}">bulk downloads</a>,
    <a href="{% url "search" %}">search</a>, <a href="{% url "cite_home" host "cite" %}">browse</a>, and an
    <a href="{% url "ngrams" %}">Ngram viewer</a>
{% else %}
explainer: The capstone of the Caselaw Access Project is a robust set of tools which facilitate access to the cases
    and their associated metadata. We currently offer five ways to access the data:
    <a href="{% api_url "api-root" %}">API</a>, <a href="{% url "bulk-download" %}">bulk downloads</a>,
    <a href="{% url "search" %}">search</a>, and <a href="{% url "cite_home" host "cite" %}">browse</a>.
{% endif %}
{% endspaceless %}
top_section_style: bg-black

# API {: class="subtitle" }
Our open-source API is the best option for anybody interested in programmatically accessing our metadata, full-text 
search, or individual cases.

[API]({% api_url "api-root" %}){: class="btn-primary" }
[DOCS]({% url "api" %}){: class="btn-secondary" }
{: class="btn-group" }

# Bulk Data {: class="subtitle" }
If you need a large collection of cases, you will probably be best served by our bulk data downloads. Bulk downloads 
for Illinois and Arkansas are available without a login, and unlimited bulk files are available to research scholars.

[BULK DATA]({% url "bulk-download" %}){: class="btn-primary" }
[DOCS]({% url "bulk-docs" %}){: class="btn-secondary" }
{: class="btn-group" }
    
# Search {: class="subtitle" }
Our search interface offers access to all of the same cases and most of our metadata with an intuitive, flexible 
interface.

[SEARCH]({% url "search" %}){: class="btn-primary" }
[DOCS]({% url "search-docs" %}){: class="btn-secondary" }
{: class="btn-group" }
 
# Browse {: class="subtitle" }
Browse and cite all of our cases sorted by jurisdiction, series, and volume.

[BROWSE]({% url "cite_home" host "cite" %}){: class="btn-primary" }
{: class="btn-group" }

{% if ngrams %}
# Ngrams {: class="subtitle" }
Explore the data by looking at how usage of text changes over time.
    
[NGRAMS]({% url "ngrams" %}){: class="btn-primary" }
{: class="btn-group" }
{% endif %}