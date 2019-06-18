{% load static %}
{% load pipeline %}
{% load api_url %}
title: API documentation
page_image: 'img/og_image/tools_api.png'
meta_description: Caselaw Access Project API Docs
top_section_style: bg-black
row_style: bg-tan
explainer: The Caselaw Access Project API, also known as CAPAPI, serves all official US court cases published in books from 1658 to 2018. The collection includes over six million cases scanned from the Harvard Law Library shelves. <a href="{% url "about" }>Learn more about the project</a>. 
extra_head: {% stylesheet 'docs' %}

  {# ==============> GETTING STARTED <============== #}
# Getting Started {: class="subtitle" }
[API]({% api_url "api-root" %}){: class="btn-primary" }

CAPAPI includes an in-browser API viewer, but is primarily intended for software developers to access caselaw 
programmatically, whether to run your own analysis or build tools for other users. API results are in JSON format with 
case text available as structured XML, presentation HTML, or plain text.

To get started with the API, you can [explore it in your browser]({% api_url "api-root" %}), or reach it from the 
command line. For example, here is a curl command to request a single case from Illinois:

`curl "{% api_url "casemetadata-list" %}?jurisdiction=ill&page_size=1"`
{: class="code-block" }

If you haven't used APIs before, you might want to check out our [search tool]({% url "search" %}) or jump down to our 
[Beginner's Introduction to APIs](#beginners-introduction-to-apis).

  {# ==============> REGISTER  <============== #}
# Registration {: class="subtitle" }

Most API queries don't require registration: check our [access limits](#access-limits) section for more details.
{: class="highlighted" }

[Click here to register for an API key]({% url "register" %}) if you need to access case text from 
non-[whitelisted](#def-whitelisted) jurisdictions.

  {# ==============> AUTHENTICATION <============== #}
# Authentication {: class="subtitle" }

Most API queries don't require registration: check our [access limits](#access-limits) section for more details.
{: class="highlighted" }

Most API requests do not need to be authenticated. However, if requests are not authenticated, you may see this response
in results from the case endpoint with `full_case=true`:
`{
  "results": [
    {
      "id": 1021505,
      ...
      "jurisdiction": {
        ...
        "whitelisted": false
      },
      "casebody": {
        "data": null,
        "status": "error_auth_required"
      }
    },
  ]
}`
{: class="code-block" }

In this example the response included a case from a non-whitelisted jurisdiction, and `casebody.data` for the case is 
therefore blank, while `casebody.status` is "error_auth_required".
  
To authenticate the request from code or the command line, you can provide an `Authorization` header:
  
`curl -H "Authorization: Token abcd12345" "{% api_url "casemetadata-list" %}?full_case=true"`
{: class="code-block" }
  
While you are [logged into this website]({% url "login" %}), all requests through the API browser will be authenticated
automatically.
  

  {# ==============> DATA FORMATS <============== #}
# Case Text Formats {: class="subtitle" data-toc-label='Data Formats' }
  
Both of these parameters must be used in conjunction with the `full_case=true`parameter.
{: class="highlighted" }
  
CAPAPI is capable of returning case text in three formats: text(default), XML, or HTML. In most instances, each case is 
represented by a JSON object which includes various pieces of metadata, and the case text itself which is located in the
`casebody` property. In both the [case browse/search results endpoint](#endpoint-cases) and the 
[individual case endpoint](#endpoint-case), the `casebody` parameter returns JSON structured plain text, but you can 
change that to either HTML or XML by setting the `body_format` query parameter to either `html` or `xml`.
  
In the [individual case endpoint](#endpoint-case), you can alternately pass `html` or `xml` to the `format` parameter to
dispense with the JSON container and return only the HTML or XML formatted case. The HTML returned using the `format` 
parameter is the same as the HTML returned in the JSON container with `body_format` set to `html`. The XML output is
significantly more verbose&mdash; It includes METS, PREMIS and structural metadata.
  
Do not set both `format` and `body_format` in the same query, and always use them with the `full_case` parameter set to 
`true`. Using the `format` parameter with the [case browse/search results endpoint](#endpoint-cases) will have no effect.
  
This is what you can expect from different format specifications using the `body_format` parameter.


Text Format (default)
{: class="topic-header" }

[{% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true]({% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true)
{: class="example-link" style="margin-top: 0px;" }

The default text format is best for natural language processing. Example response data:

`"data": {
      "head_matter": "Fifth District\n(No. 70-17;\nThe People of the State of Illinois ...",
      "opinions": [
          {
              "author": "Mr. PRESIDING JUSTICE EBERSPACHER",
              "text": "Mr. PRESIDING JUSTICE EBERSPACHER\ndelivered the opinion of the court: ...",
              "type": "majority"
          }
      ],
      "judges": [],
      "parties": [
          "The People of the State of Illinois, Plaintiff-Appellee, v. Danny Tobin, Defendant-Appellant."
      ],
      "attorneys": [
          "John D. Shulleriberger, Morton Zwick, ...",
          "Robert H. Rice, State’s Attorney, of Belleville, for the Peop ..."
      ]
  }
}`
{: class="code-block" }

In this example, `"head_matter"` is a string representing all text printed in the volume before the text prepared by 
judges. `"opinions"` is an array containing a dictionary for each opinion in the case. `"judges"`, `"parties"`, and 
`"attorneys"` are particular substrings from `"head_matter"` that we believe to refer to entities involved with the 
case.
      

XML Format
{: class="topic-header" }

[{% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true&body_format=xml]({% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true&body_format=xml)
{: class="example-link" style="margin-top: 0px;" }

The XML format is best if your analysis requires more information about pagination, formatting, or page layout. It 
contains a superset of the information available from body_format=text, but requires parsing XML data. Example 
response data:
      
`"data": "<?xml version='1.0' encoding='utf-8'?>\n<casebody ..."`
{: class="code-block" }

HTML Format
{: class="topic-header" }

[{% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true&body_format=html]({% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true&body_format=html)
{: class="example-link" style="margin-top: 0px;" }
      
The HTML format is best if you want to show readable, formatted caselaw to humans. It represents a best-effort attempt 
to transform our XML-formatted data to semantic HTML ready for CSS formatting of your choice. Example response data:
      
`"data": "<section class=\"casebody\" data-firstpage=\"538\" data-lastpage=\"543\"> ..."`
{: class="code-block" }



{# ====> PAGINATION <==== #}
# Pagination and Counts {: class="subtitle" data-toc-label='Pagination and Counts' }
  
Queries by default return 100 results per page, but you may request a smaller number using the `page_size` parameter:
  
`curl "{% api_url "casemetadata-list" %}?jurisdiction=ill&page_size=1"`
{: class="code-block" }
  
We use [cursor](#def-cursor)-based pagination, meaning we keep track of where you are in the results set on 
the server, and you can access each page of results by using the link in the `"previous"` and `"next"` keys of the 
response:
  
`{
  "count": 183149,
  "next": "{% api_url "casemetadata-list" %}?cursor=cD0xODMyLTEyLTAx",
  "previous": "{% api_url "casemetadata-list" %}?cursor=bz0xMCZyPTEmcD0xODI4LTEyLTAx"
  ...
}`
{: class="code-block" }

Responses also include a `"count"` key. Occasionally this may show `"count": null`, indicating that the total count for
a particular query has not yet been calculated.
  

  {# ==============> ACCESS LIMITS <============== #}
# Access Limits {: class="subtitle" }
  
The agreement with our project partner, [Ravel](http://ravellaw.com), requires us to limit access to the full
text of cases to no more than 500 cases per person, per day. This limitation does not apply to 
[researchers](#def-researchers) who agree to certain restrictions on use and redistribution. Nor does this restriction 
apply to cases issued in [jurisdictions](#def-jurisdiction) that make their newly issued cases freely 
available online in an authoritative, citable, machine-readable format. We call these 
[whitelisted](#def-whitelisted) jurisdictions. Currently, Illinois and Arkansas are the only whitelisted
jurisdictions.
  
We would love to whitelist more jurisdictions! If you are involved in US case publishing at the state or federal level,
we'd love to talk to you about making the transition to digital-first publishing. Please 
[contact us]({% url "contact" %}) and introduce yourself!
  
If you qualify for unlimited access as a research scholar, you can request a research agreement by
[creating an account]({% url "register" %}) and then visiting your [account page]({% url "user-details" %}).
  
  
In addition, under our agreement with Ravel (now owned by Lexis-Nexis), Ravel must negotiate in good faith to provide 
bulk access to anyone seeking to make commercial use of this data. 
[Click here to contact Ravel for more information](http://info.ravellaw.com/contact-us-form) or 
[contact us]({% url "contact" %}) and we will put you in touch with Ravel.
  
  
Unregistered Users
{: class="topic-header", id="def-unregistered-user" }

* Access all metadata
{: class="list-group-item" add_list_class="parameter-list" }
* Unlimited API access to all cases from [whitelisted](#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }
* Bulk Download all cases from [whitelisted](#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }

Registered Users
{: class="topic-header", id="def-registered-user" }

* Access all metadata
{: class="list-group-item" add_list_class="parameter-list" }
* Unlimited API access to all cases from [whitelisted](#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }
* Access to 500 cases per day from non-[whitelisted](#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }
* Bulk Download all cases from [whitelisted](#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }


Researchers
{: class="topic-header", id="def-researchers" }

* Access all metadata
{: class="list-group-item" add_list_class="parameter-list" }
* Unlimited API access to all cases
{: class="list-group-item" add_list_class="parameter-list" }
* Bulk Downloads from all jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }

Commercial Users
{: class="topic-header", id="def-researchers" }

[Click here to contact Ravel for more information.](http://info.ravellaw.com/contact-us-form)

{# ==============> EXAMPLES <============== #}
# Usage Examples  {: class="subtitle" data-toc-label='Examples' }
  
This is a non-exhaustive set of examples intended to orient new users. The [endpoints](#endpoints) section contains more
comprehensive documentation about the URLs and their parameters.
  
{# ====> single case <==== #}
Retrieve a single case by ID
{: class="topic-header" }

[{% api_url "casemetadata-detail" case_id %}]({% api_url "casemetadata-detail" case_id %})
{: class="example-link" style="margin-top: 0px;" }

This example uses the [single case](#endpoint-case) endpoint, and will retrieve the metadata for a single 
case.

Modification with Parameters:
{: class="list-header mb-2" }

* **Standalone HTML-formatted Case**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "casemetadata-detail" case_id %}?full_case=true&format=html]({% api_url "casemetadata-detail" case_id %}?full_case=true&format=html)
    {: add_list_class="example-mod-url" }
    * This will return a lightly styled, standalone HTML representation of the case with no accompanying metadata.
    {: add_list_class="example-mod-description" }
* **Plain Text Case in JSON container with metadata**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "casemetadata-detail" case_id %}]({% api_url "casemetadata-detail" case_id %})
    {: add_list_class="example-mod-url" }
    * This will return a lightly styled, standalone HTML representation of the case with no accompanying metadata.
    {: add_list_class="example-mod-description" }
* **Raw original XML document, with METS data**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "casemetadata-detail" case_id %}?full_case=true&body_format=xml]({% api_url "casemetadata-detail" case_id %}?full_case=true&body_format=xml)
    {: add_list_class="example-mod-url" }
    * To get the document by itself, without the JSON enclosure and metadata, use the `format` parameter. Set it to HTML
     and get a display-ready, standalone HTML document.
    {: add_list_class="example-mod-description" }


{# ====> filter cases <==== #}
Retrieve a list of cases using a metadata filter
{: class="topic-header" }

[{% api_url "casemetadata-list" %}?cite={{ case_metadata.citations.0.cite }}]({% api_url "casemetadata-list" %}?cite={{ case_metadata.citations.0.cite }})
{: class="example-link" style="margin-top: 0px;" }

This example uses the [cases](#endpoint-cases) endpoint, and will retrieve every case with the citation 
{{ case_metadata.citations.0.cite }}. 

There are many parameters with which you can filter the cases result. Check the 
[cases](#endpoint-cases) endpoint documentation for a complete list of the parameters, and what values they accept.

Modification with Parameters:
{: class="list-header mb-2" }

* **Add a date range filter**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "casemetadata-list" %}?cite={{ case_metadata.citations.0.cite }}&decision_date_min=1900-12-30&decision_date_max=2000-12-30]({% api_url "casemetadata-list" %}?cite={{ case_metadata.citations.0.cite }}&decision_date_min=1900-12-30&decision_date_max=2000-12-30)
    {: add_list_class="example-mod-url" }
    * You can combine any of these parameters to refine your search. Here, we have the same search as in the first 
    example, but will only receive results from within the specified dates.
    {: add_list_class="example-mod-description" }


{# ====> Full Text Search <==== #}
Simple Full-Text Search
{: class="topic-header" }

[{% api_url "casemetadata-list" %}?search=insurance]({% api_url "casemetadata-list" %}?search=insurance)
{: class="example-link" style="margin-top: 0px;" }

This example performs a simple full-text case search which finds all cases containing the word "insurance." 

There are many parameters with which you can filter the cases result. Check the [cases](#endpoint-cases) endpoint 
documentation for a complete list of the parameters, and what values they accept.

Modification with Parameters:
{: class="list-header mb-2" }

* **Add Search Term**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "casemetadata-list" %}?search=insurance Peoria]({% api_url "casemetadata-list" %}?search=insurance Peoria)
    {: add_list_class="example-mod-url" }
    * You can narrow your search results by adding terms, separated by spaces. This search will only include cases that contain both "insurance" and Peoria.
    {: add_list_class="example-mod-description" }
* **Filter Search With Metadata**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "casemetadata-list" %}?search=insurance Peoria&jurisdiction=ill]({% api_url "casemetadata-list" %}?search=insurance Peoria&jurisdiction=ill)
    {: add_list_class="example-mod-url" }
    * These queries can be filtered using other metadata fields. This query will perform the prior search while limiting
     the query to the Illinois jurisdiction.
    {: add_list_class="example-mod-description" }


{# ====> Get All Reporters <==== #}
Get all reporters in a jurisdiction
{: class="topic-header" }

[{% api_url "reporter-list" %}?jurisdictions=ark]({% api_url "reporter-list" %}?jurisdictions=ark)
{: class="example-link" style="margin-top: 0px;" }

This example uses the [reporters](#endpoint-reporters) endpoint, and will retrieve all reporters in Arkansas.


{# ==============> ENDPOINTS <============== #}
# Endpoints {: class="subtitle" }

{# ==============> BASE <============== #}
API Base
{: class="topic-header", id="endpoint-base" }

[{% api_url "api-root" %}]({% api_url "api-root" %})
{: class="endpoint-link" style="margin-top: 0px;" }

This is the base [endpoint](#def-endpoint) of CAPAPI. It just lists all of the available 
[endpoints](#def-endpoint).
{: class="endpoint description" }


{# ==============> CASES <============== #}
Case Browse/Search Endpoint
{: class="topic-header", id="endpoint-cases" }

[{% api_url "api-root" %}]({% api_url "api-root" %})
{: class="endpoint-link" style="margin-top: 0px;" }

This is the primary endpoint; you use it to browse, search for, and retrieve cases. If you know the numeric ID of your 
case in our system, you can append it to the [path](#def-path) to retrieve a [single case](#endpoint-case).
{: class="endpoint description" }

Endpoint Parameters:
{: class="list-header mb-2" }

* **Add Search Term**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "casemetadata-list" %}?search=insurance Peoria]({% api_url "casemetadata-list" %}?search=insurance Peoria)
    {: add_list_class="example-mod-url" }
    * You can narrow your search results by adding terms, separated by spaces. This search will only include cases that contain both "insurance" and Peoria.
    {: add_list_class="example-mod-description" }
* **Filter Search With Metadata**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "casemetadata-list" %}?search=insurance Peoria&jurisdiction=ill]({% api_url "casemetadata-list" %}?search=insurance Peoria&jurisdiction=ill)
    {: add_list_class="example-mod-url" }
    * These queries can be filtered using other metadata fields. This query will perform the prior search while limiting
     the query to the Illinois jurisdiction.
    {: add_list_class="example-mod-description" }

      
Endpoint Parameters:
{: class="list-header mb-2" }

* `name_abbreviation`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * An arbitrary [string](#def-string).
    {: class="param-data-type" }
    * e.g. `People v. Smith`
    {: class="param-description" }
* `decision_date_min`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * `YYYY-MM-DD`
    {: class="param-data-type" }
* `decision_date_max`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * `YYYY-MM-DD`
    {: class="param-data-type" }
* `docket_number`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * An arbitrary [string](#def-string)
    {: class="param-data-type" }
* `citation`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * e.g. `1 Ill. 21`
    {: class="param-data-type" }
* `reporter`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * integer
    {: class="param-data-type" }
    * a [reporter](#endpoint-reporters) id
    {: class="param-description" }
* `court`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * [slug](#def-slug)
    {: class="param-data-type" }
    * a [court](#endpoint-courts) [slug](#def-slug)
    {: class="param-description" }
* `court_id`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * integer
    {: class="param-data-type" }
    * a [court](#endpoint-courts) id
    {: class="param-description" }
* `jurisdiction`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * [slug](#def-slug)
    {: class="param-data-type" }
    * a [jurisdiction](#endpoint-jurisdictions) [slug](#def-slug)
    {: class="param-description" }
* `search`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * An arbitrary [string](#def-string)
    {: class="param-data-type" }
    * A full-text search query
    {: class="param-description" }
* `cursor`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * An randomly generated [string](#def-string)
    {: class="param-data-type" }
    * This field contains a value that we generate which will bring you to a specific page of results.
    {: class="param-description" }
            
            
{# ==============> CASE <============== #}
Single Case Endpoint
{: class="topic-header", id="endpoint-case" }

[{% api_url "casemetadata-detail" case_id %}]({% api_url "casemetadata-detail" case_id %})
{: class="endpoint-link" style="margin-top: 0px;" }

Use this endpoint to retrieve a single case.
{: class="endpoint description" }

Endpoint Parameters:
{: class="list-header mb-2" }

* `full_case`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * `true` or `false`
    {: class="param-data-type" }
    * When set to `true`, this parameter loads the case body. It is required for setting both `body_format` and `format`.
    {: class="param-description" }
* `body_format`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * `html` or `xml`
    {: class="param-data-type" }
    * This will return a JSON enclosure with metadata, and a field containing the case in XML or HTML.
    {: class="param-description" }
* `format`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * `html` or `xml`
    {: class="param-data-type" }
    * This will return the case in HTML or its original XML with no JSON enclosure or metadata.
    {: class="param-description" }
* `cursor`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * An randomly generated [string](#def-string)
    {: class="param-data-type" }
    * This field contains a value that we generate which will bring you to a specific page of results.
    {: class="param-description" }
        
        
Here's what you can expect when you request a single case. Everything under 
`casebody`{: class="code-example-casebody-section" } is only returned if `full_case=true` is set. In the 
[cases](#endpoint-cases) endpoint, you'd get a list of these in a JSON object which also included pagination information
and result counts.


<pre class="code-block">{
  "id": <span class="json-data-type">(integer)</span>
  "url": <span class="json-data-type"><a href="#def-url">(url)</a></span>,
  "name": <span class="json-data-type"><a href="#def-string">(string)</a></span>,
  "name_abbreviation": <span class="json-data-type"><a href="#def-string">(string)</a></span>,
  "decision_date": <span class="json-data-type">YYYY-MM-DD</span>,
  "docket_number": <span class="json-data-type"><a href="#def-string">(string)</a></span>,
  "first_page": <span class="json-data-type"><a href="#def-string">(string)</a> (generally a number)</span>,
  "last_page": <span class="json-data-type"><a href="#def-string">(string)</a> (generally a number)</span>,
  "citations": [
      {
          "type": <span class="json-data-type">"official" or "parallel"</span>,
          "cite": <span class="json-data-type"><a href="#def-string">(string)</a></span>
      }
  ],
  "volume": {
      "url": <span class="json-data-type"><a href="#def-url">(url)</a></span>,
      "volume_number": <span class="json-data-type"><a href="#def-string">(string)</a> (generally a number)</span>
  },
  "reporter": {
      "url": <span class="json-data-type"><a href="#def-url">(url)</a></span>,
      "full_name": <span class="json-data-type"><a href="#def-string">(string)</a></span>
  },
  "court": {
      "url": <span class="json-data-type"><a href="#def-url">(url)</a></span>,
      "id": <span class="json-data-type">(integer)</span>,
      "slug": <span class="json-data-type"><a href="#def-slug">(slug)</a></span>,
      "name": <span class="json-data-type"><a href="#def-string">(string)</a></span>,
      "name_abbreviation": <span class="json-data-type"><a href="#def-string">(string)</a></span>
  },
  "jurisdiction": {
      "url": <span class="json-data-type"><a href="#def-url">(url)</a></span>,
      "id": <span class="json-data-type">(integer)</span>,
      "slug": <span class="json-data-type"><a href="#def-slug">(slug)</a></span>,
      "name": <span class="json-data-type"><a href="#def-string">(string)</a></span>,
      "name_long": <span class="json-data-type"><a href="#def-string">(string)</a></span>,
      "whitelisted": <span class="json-data-type">"true" or "false"</span>
  },
  <span class="code-example-casebody-section">
  "casebody": {
      "data": {
          "judges": [],
          "head_matter": <span class="json-data-type"><a href="#def-string">(string)</a></span>
          "attorneys": [
            <span class="json-data-type"><a href="#def-string">(string)</a></span>
          ],
          "opinions": [
              {
                  "type": <span class="json-data-type"><a href="#def-string">(string)</a></span>,
                  "author": <span class="json-data-type"><a href="#def-string">(string)</a></span>,
                  "text": <span class="json-data-type"><a href="#def-string">(string)</a></span>
              }
          ],
          "parties": [
              <span class="json-data-type"><a href="#def-string">(string)</a></span>
          ]
      },
      "status": <span class="json-data-type">should be "ok"</span>
  }
  </span>
}</pre>


{# ==============> reporters <============== #}
Reporters Endpoint
{: class="topic-header", id="endpoint-reporters" }

[{% api_url "reporter-list" %}]({% api_url "reporter-list" %}){: class="endpoint-link" }
{: class="endpoint-link" style="margin-top: 0px;" }

This will return a list of reporter series.
{: class="endpoint description" }


Endpoint Parameters:
{: class="list-header mb-2" }

* `full_name`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * e.g. Illinois Appellate Court Reports
    {: class="param-data-type" }
    * the full reporter name
    {: class="param-description" }
* `short_name`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * e.g. Ill. App.
    {: class="param-data-type" }
    * the abbreviated name for the reporter
    {: class="param-description" }
* `start_year`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * YYYY
    {: class="param-data-type" }
    * the earliest year reported on in the series
    {: class="param-description" }
* `end_year`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * YYYY
    {: class="param-data-type" }
    * the latest year reported on in the series
    {: class="param-description" }
* `volume_count`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * integer
    {: class="param-data-type" }
    * filter on the number of volumes in a reporter series
    {: class="param-description" }
* `cursor`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * a randomly generated [string](#def-string)
    {: class="param-data-type" }
    * This field contains a value that we generate which will bring you to a
     specific page of results.
    {: class="param-description" }


{# ==============> jurisdictions <============== #}
Jurisdictions
{: class="topic-header", id="endpoint-jurisdictions" }

[{% api_url "jurisdiction-list" %}]({% api_url "jurisdiction-list" %}){: class="endpoint-link"  }
{: class="endpoint-link" style="margin-top: 0px;" }

This will return a list of jurisdictions.
{: class="endpoint description" }
      
Endpoint Parameters:
{: class="list-header mb-2" }

* `id`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * integer
    {: class="param-data-type" }
    * get jurisdiction by ID
    {: class="param-description" }
* `name`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * e.g. `Ill.`
    {: class="param-data-type" }
    * abbreviated jurisdiction name
    {: class="param-description" }
* `name_long`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * e.g. `Illinois`
    {: class="param-data-type" }
    * full jurisdiction name
    {: class="param-description" }
* `whitelisted`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * true` or `false`
    {: class="param-data-type" }
    * filter for [whitelisted](#def-whitelisted) cases
    {: class="param-description" }
* `slug`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * a [slug](#def-slug)
    {: class="param-data-type" }
    * filter on the jurisdiction [slug](#def-slug)
    {: class="param-description" }
* `cursor`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * a randomly generated [string](#def-string)
    {: class="param-data-type" }
    * This field contains a value that we generate which will bring you to a
     specific page of results.
    {: class="param-description" }

{# ==============> courts <============== #}
Courts
{: class="topic-header", id="endpoint-courts" }

[{% api_url "court-list" %}]({% api_url "court-list" %}){: class="endpoint-link"  }
{: class="endpoint-link" style="margin-top: 0px;" }

This will return a list of courts.
{: class="endpoint description" }
      
Endpoint Parameters:
{: class="list-header mb-2" }

* `id`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * integer
    {: class="param-data-type" }
    * get courts by ID
    {: class="param-description" }
* `slug`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * a [slug](#def-slug)
    {: class="param-data-type" }
    * filter on the court [slug](#def-slug)
    {: class="param-description" }
* `name`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * e.g. `Illinois Appellate Court`
    {: class="param-data-type" }
    * full court name
    {: class="param-description" }
* `name_abbreviation`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * e.g. `Ill. App. Ct.`
    {: class="param-data-type" }
    * abbreviated court name
    {: class="param-description" }
* `jurisdiction`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * [slug](#def-slug)
    {: class="param-data-type" }
    * [jurisdiction](#endpoint-jurisdictions) [slug](#def-slug)
    {: class="param-description" }
* `cursor`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * a randomly generated [string](#def-string)
    {: class="param-data-type" }
    * This field contains a value that we generate which will bring you to a
     specific page of results.
    {: class="param-description" }
            


{# ==============> volumes <============== #}
Volumes
{: class="topic-header", id="endpoint-volumes" }

[{% api_url "volumemetadata-list" %}]({% api_url "volumemetadata-list" %}){: class="endpoint-link" }
{: class="endpoint-link" style="margin-top: 0px;" }

This will return a complete list of volumes.
{: class="endpoint description" }
      
Endpoint Parameters:
{: class="list-header mb-2" }

* `cursor`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * a randomly generated [string](#def-string)
    {: class="param-data-type" }
    * This field contains a value that we generate which will bring you to a
     specific page of results.
    {: class="param-description" }
        

{# ==============> Citations <============== #}
Citations
{: class="topic-header", id="endpoint-citations" }

[{% api_url "citation-list" %}]({% api_url "citation-list" %}){: class="endpoint-link" }
{: class="endpoint-link" style="margin-top: 0px;" }

This will return a list of citations.
{: class="endpoint description" }
      
Endpoint Parameters:
{: class="list-header mb-2" }

* `cursor`{: class="parameter-name" }
{: class="list-group-item" add_list_class="parameter-list" }
    * a randomly generated [string](#def-string)
    {: class="param-data-type" }
    * This field contains a value that we generate which will bring you to a
     specific page of results.
    {: class="param-description" }

  {# ==============> BEGINNERS <============== #}
# Beginner's Introduction to APIs  {: class="subtitle" data-toc-label='Intro to APIs' }
  
Are you a little lost in all the technical jargon, but still want to give the API a shot? This is a good place to start!
 This is by no means a complete introduction to using [APIs](#def-api), but it might be just enough to help situate a 
 technically inclined person who's a bit outside of their comfort zone. If you've had enough and would prefer to just 
 access the cases using a human-centric interface, please check out our [search tool]({% url 'search' %}). 
  
Fundamentally, an API is no different from a regular website: A program on your computer, such as a web browser or 
[curl](#def-curl) sends a bit of data to a [server](#def-server), the server processes that data, and then sends a 
response. If you know how to read a [url](#def-url), you can interact with web-based services in ways that aren't 
limited to clicking on the links and buttons on the screen. 
  
Consider the following [url](#def-url), which will 
[perform a google search for the word "CAP."](https://www.google.com/search?q=CAP")
  
`https://www.google.com/search?q=CAP`
{: class="code-block" }
  
Let's break it down into its individual parts:
  
`https://`
{: class="code-block" }
  
This first part tells your web browser which protocol to use: this isn't very important for our purposes, so we'll 
ignore it.
  
`www.google.com`
{: class="code-block" }
  
The next part is a list of words, separated by periods, between the initial double-slash, and before the subsequent 
single slash. Many people generically refer to this as the domain, which is only partly true, but the reason why that's 
not entirely true isn't really important for our purposes; the important consideration here is that it points to a 
specific [server](#def-server), which is just another computer on the internet. 

`/search`
{: class="code-block" }
  
The next section, which is comprised of everything between the slash after the server name and the question mark, is 
called the [path](#def-path). It's called a path because, in the earlier days of the web, it was a 'path' through 
folders/directories to find a specific file on the web server. These days, it's more likely that the path will point 
to a specific [endpoint](#def-endpoint).
  
  
You can think of an endpoint as a distinct part of a program, which could require specific inputs, and/or provide 
different results. For example, the "login" endpoint on a website might accept a valid username and a password for 
input, and return a message that you've successfully logged in. A "register" endpoint might accept various bits of 
identifying information, and return a screen that says your account was successfully registered.
  
  
Though there is only one part of this particular path, `search`, developers usually organize paths into hierarchical 
lists separated by slashes. Hypothetically, if the developers at Google decided that one generalized search endpoint 
wasn't sufficiently serving people who wanted to search for books or locations, they could implement more specific 
endpoints such as `/search/books` and `/search/locations`.
  
`?q=CAP`
{: class="code-block" }
  
The final section of the URL is where you'll find the [parameters](#def-parameter), and is comprised of everything 
after the question mark. Parameters are a way of passing individual, labelled pieces of information to the endpoint to 
help it perform its job. In this case, the parameter tells the `/search` endpoint what to search for. Without this 
parameter, the response wouldn't be particularly useful.
  
A URL can contain many parameters, separated by ampersands, but in this instance, there is only one parameter: the 
rather cryptically named "q," which is short for "query," which has a value of "CAP." Parameter names are arbitrary— 
Google's developers could just as easily have set the parameter name to `?query=CAP`, but decided that "q" would 
sufficiently communicate its purpose. 
  
The Google developers designed their web search endpoint to accept other parameters, too. For example, there is an even 
more cryptically named parameter, 'tbs' which will limit the age of the documents returned in the search results. The 
parameters `?q=CAP&tbs=qdr:y` will perform a web search for "CAP" and limit the results to documents less than a year 
old. 
  
So when you're working with CAPAPI, the same principles apply. Rather than http://www.google.com, you'll be using 
{% api_url "api-root" %}. Rather than using the /search?q= endpoint and parameter, you'll be using one of our 
[endpoints](#endpoints) and the parameters we've defined. One important difference is the purpose of the structured data
we're returning, vs. the visual, browser-oriented data that google is returning with their search engine. 
  
When you perform a query in a web browser using our API, there are some links and buttons, but the data itself is in a 
text-based format with lots of brackets and commas. This format is called JSON, or JavaScript Object Notation. We use 
this format because software developers can easily utilize data in that format in their own programs. We do intend to 
have a more user-friendly case browser at some point soon, but we're not quite there yet. 
  
OK! That about does it for our beginner's introduction to web-based APIs. Please check out our 
[usage examples](#usage-examples") section to see some of the ways you can put these principles to work in CAPAPI. If you have 
any suggestions for making this documentation better, we'd appreciate your taking the time to let us know in an issue 
report in [our repository on github.com](https://github.com/harvard-lil/capstone/issues). 
  
Thanks, and good luck!
  

{# ==============> PROBLEMS <============== #}
# Reporting Problems and Enhancement Requests {: class="subtitle" data-toc-label='Report Issues' }
  
We are serving an imperfect, living dataset through an API that will forever be a work-in-progress. We work hard to hunt 
down and fix problems in both the API and the data, but a robust user base will uncover problems more quickly than our 
small team could ever hope to. Here's the best way to report common types of errors.
  
* [Our data errata](https://github.com/harvard-lil/capstone#errata)
* [Our issue tracker](https://github.com/harvard-lil/capstone/issues)
* [Our Github repository](https://github.com/harvard-lil/capstone)


Jumbled or Misspelled Words in Case Text:
{: class="list-header mb-1" }

For now, we're not accepting bug reports for [OCR](#def-ocr) problems. While our data is good quality for OCR'd text, we
fully expect these errors in every case.  We're working on the best way to tackle this.
{: class="mt-0" }


Typos or Broken Links in Documentation or Website, API Error Messages or Performance Problems, and Missing Features:
{: class="list-header mb-1" }

First, please check our existing [issues](https://github.com/harvard-lil/capstone/issues) to see if someone has already
reported the problem. If so, please feel free to comment on the issue to add information. We'll update the issue when 
there's more information about the issue, so if you'd like notifications, click on the "Subscribe" button on the 
right-hand side of the screen. If no issue exists, create a new issue, and we'll get back to you as soon as we can.
{: class="mt-0" }


Incorrect Metadata or Improperly Labelled data in XML:
{: class="list-header mb-1" }

First, check our [errata](https://github.com/harvard-lil/capstone#errata) to see if this is a known issue. Then, check 
our existing [issues](https://github.com/harvard-lil/capstone/issues) to see if someone has already reported the 
problem. If so, please feel free to comment on the issue to add context or additional instances that the issue owner 
didn't report. We'll update the issue when there's more information about the issue, so if you'd like notifications, 
click on the "Subscribe" button on the right-hand side of the screen. If no issue exists, create a new issue and we'll 
get back to you as soon as we can.
{: class="mt-1" }


{# ==============> GLOSSARY <============== #}
# Glossary  {: class="subtitle" }
  
This is a list of technical or project-specific terms we use in this documentation. These are stub definitions to help 
you get unstuck, but they should not be considered authoritative or complete. A quick Google search should provide more 
context for any of these terms.

* API
{: class="list-header mb-0" id="def-api" }
* API is an acronym for Application Programming Interface. Broadly, it is a way for one computer program to transfer 
data to another computer program. CAPAPI is a [RESTful](#def-restful) API designed to distribute court case data.
{: class="mt-1" }


* Character
{: class="list-header mb-0" id="def-character" }
* A letter, number, space, or piece of punctuation. Multiple characters together make up a [string](#def-string).
{: class="mt-1" }
  
  
* Special Character
{: class="list-header mb-0" id="def-special-character" }
* Special characters are characters that have programmatic significance to a program. The "specialness" of any given character is determined by the context in which it's used. For example, you can't add a bare question mark to your path because they indicate to the server that everything after them is a [parameter](#def-parameter).
{: class="mt-1" }


* Command Line
{: class="list-header mb-0" id="def-command-line" }
* This is the textual interface for interacting with a computer. Rather than interacting with the system through windows
 and mouse clicks, commands are typed and output is rendered in its textual form. On mac, the default Command Line 
 program is Terminal. On Windows, the program is cmd.exe.
{: class="mt-1" }


* curl
{: class="list-header mb-0" id="def-curl" }
* [curl](https://curl.haxx.se/) is a simple [command line](#def-command-line) tool for retrieving data over the 
internet. It's similar to a web browser in that it will retrieve the contents of a [url](#def-url), but it will dump the
 text contents to a terminal, rather than show a rendered version in a graphical browser window.
{: class="mt-1" }
  
  
* Endpoint
{: class="list-header mb-0" id="def-endpoint" }
* You can think of an endpoint as a distinct part of a program, which could require specific inputs, and/or provide different results. For example, the "login" endpoint on a website might accept a valid username and a password for input, and return a message that you've successfully logged in. A "register" endpoint might accept various bits of identifying information, and return a screen that says your account was successfully registered.
{: class="mt-1" }
  

* Jurisdiction
{: class="list-header mb-0" id="def-jurisdiction" }
* The jurisdiction of a case or volume is the political division it belongs to, such as the United States, a state, a territory, a tribe, or the District of Columbia. Volumes that collect cases from a region have the jurisdiction "Regional." Cases from tribal courts (other than Navajo Nation) temporarily have the jurisdiction "Tribal Jurisdictions" while we verify the correct jurisdiction for each tribal court.
{: class="mt-1" }


* OCR
{: class="list-header mb-0" id="def-ocr" }
* OCR is a process in which a computer attempts to create text from an image of text. The text in our cases is OCR-derived using scanned case reporter pages as source images.
{: class="mt-1" }


* RESTful
{: class="list-header mb-0" id="def-restful" }
* A RESTful [API](#def-api) is based on [HTTP](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol), and makes use of its built-in verbs(commands), such as GET and POST.
{: class="mt-1" }


* Reporter
{: class="list-header mb-0" id="def-reporter" }
* In this project, we use the term 'reporter' to refer to a reporter series. We'd consider F2d. a reporter.
{: class="mt-1" }


* Server
{: class="list-header mb-0" id="def-server" }
* A server is just a computer on the internet that was configured to respond to requests from other computers. A web server will respond to requests from a web browser. An email server will respond to requests from email programs, and or other email servers which are sending it messages.
{: class="mt-1" }


* Slug
{: class="list-header mb-0" id="def-slug" }
* A [string](#def-string) with [special characters](#def-special-character) removed for ease of inclusion in a [url](#def-url).
{: class="mt-1" }


* String
{: class="list-header mb-0" id="def-string" }
* A string, as a type of data, just means an arbitrary list (or string) of [characters](#def-character). A word is a string. This whole sentence is a string. "h3ll0.!" is a string. This whole document is a string.
{: class="mt-1" }


* Top-Level Domain
{: class="list-header mb-0" id="def-tld" }
* The suffix to a domain name, such as `.com`, `.edu` or `.co.uk`.
{: class="mt-1" }


* URL
{: class="list-header mb-0" id="def-url" }
* A URL, or Uniform Resource Locator, is an internet address that generally contains a communication protocol, a server name, a path to a file or endpoint, and possibly parameters to pass to the endpoint.
{: class="mt-1" }


* URL Parameter
{: class="list-header mb-0" id="def-parameter" }
* For our purposes, a parameter is just a piece of data with a label that can be passed to an [endpoint](#def-endpoint) in a web request.
{: class="mt-1" }


* URL Path
{: class="list-header mb-0" id="def-path" }
* The URL path begins with the slash after the [top-level domain](#def-tld) and ends with the question mark that signals the beginning of the [parameters](#def-parameter). It was originally intended to point to a file on the server's hard drive, but these days it's just as likely to point to an application [endpoint](#def-endpoint).
{: class="mt-1" }


* Whitelisted
{: class="list-header mb-0" id="def-whitelisted" }
* While most cases in the database are subject to a 500 case per day access limit, jurisdictions that publish their cases in a citable, machine-readable format are not subject to this limit. [Click here for more information on access limits, what type of users aren't subject to them, and how you can eliminate them in your legal jurisdiction.](#access-limits)
{: class="mt-1" }


* Cursor
{: class="list-header mb-0" id="def-cursor" }
* This property, populated with a random alphanumeric value, is present in all endpoints. It represents a specific page 
of results for a query. You can get the value of the cursor for the next and previous pages from the cursor parameter in
the urls in the `next` and `previous` fields.
{: class="mt-1" }
