{% load static %}
{% load api_url %}
title: Tools
page_image: img/og_image/tools.png
meta_description: Tools for accessing caselaw
explainer: Tools maintained by CAP to browse and download caselaw.
top_section_style: bg-black
row_style: bg-tan

# The API {: class="subtitle" data-toc-label='API' }
Our open-source API is the best option for anybody interested in programmatically accessing our metadata, full-text 
search, or individual cases.

[API]({% api_url "api-root" %}){: class="btn-primary" }
[DOCS]({% url "api" %}){: class="btn-secondary" }
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

# Download {: class="subtitle" }
Our downloads directory includes derivative datasets, bulk exports, and summaries from the Caselaw Access Project. 

[DOWNLOADS]({% url "download-files" "" %}){: class="btn-primary" }
{: class="btn-group" }

# Historical Trends {: class="subtitle" }
Explore the data by looking at how usage of text changes over time.
    
[HISTORICAL TRENDS]({% url "trends" %}){: class="btn-primary" }
[DOCS]({% url "trends-docs" %}){: class="btn-secondary" }
{: class="btn-group" }
