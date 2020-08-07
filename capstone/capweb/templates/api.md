{% load static %}
{% load pipeline %}
{% load api_url %}
title: API documentation
page_image: img/og_image/tools_api.png
meta_description: Caselaw Access Project API Docs
top_section_style: bg-black
row_style: bg-tan
explainer: The Caselaw Access Project API, also known as CAPAPI, serves all official US court cases published in books from 1658 to 2018. The collection includes over six million cases scanned from the Harvard Law School Library shelves. <a href="{% url "about" }>Learn more about the project</a>.

{# ==============> GETTING STARTED <============== #}
# Getting Started {: class="subtitle" data-toc-label='Start Here' }
[API]({% api_url "api-root" %}){: class="btn-primary" }

CAPAPI includes an in-browser API viewer, but is primarily intended for software developers to access caselaw 
programmatically, whether to run your own analysis or build tools for other users. API results are in JSON format with 
case text available as structured XML, presentation HTML, or plain text.

To get started with the API, you can [explore it in your browser]({% api_url "api-root" %}), or reach it from the 
command line. For example, here is a curl command to request a single case from Illinois:

    curl "{% api_url "cases-list" %}?jurisdiction=ill&page_size=1"

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

    {
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
    }

In this example the response included a case from a non-whitelisted jurisdiction, and `casebody.data` for the case is 
therefore blank, while `casebody.status` is "error_auth_required".
  
To authenticate a request from the command line or a program, pass the `Authorization` header with your request. 
<span class="highlighted">The format of the `Authorization` header value is important: Use the string `Token` followed 
by a space, followed by your API key.</span> 

__Example:__ With an API key of `abcd12345`, you would pass `Token abcd12345` to the 
`Authorization` header.

A curl command would look like this:
  
    curl -H "Authorization: Token abcd12345" "{% api_url "cases-list" %}{{case.id}}/?full_case=true"

In a program, (python's request library in this example,) it would look something like this:

    response = requests.get(
        '{% api_url "cases-list" %}{{case.id}}/?full_case=true',
        headers={'Authorization': 'Token abcd12345'}
    )
  
If you are [logged into this website]({% url "login" %}) and accessing the API through a web browser, all requests 
will be authenticated automatically.
  

{# ==============> DATA FORMATS <============== #}
# Case Text Formats {: class="subtitle" data-toc-label='Data Formats' }
  
The `body_format` query parameter controls the format of full case text when using the `full_case=true` parameter.
  
CAPAPI cases are always returned as JSON objects. By default the `casebody` JSON field returns structured plain text,
but you can change that to either HTML or XML by setting the `body_format` query parameter to either `html` or `xml`.
  
This is what you can expect from different format specifications using the `body_format` parameter:

Text Format (default)
{: class="topic-header" }

[{% api_url "cases-list" %}?jurisdiction=ill&full_case=true]({% api_url "cases-list" %}?jurisdiction=ill&full_case=true)
{: class="example-link mt-0" }

The default text format is best for natural language processing. Example response data:

    "data": {
          "head_matter": "Fifth District\n(No. 70-17;\nThe People of the State of Illinois ...",
          "opinions": [
              {
                  "author": "Mr. PRESIDING JUSTICE EBERSPACHER",
                  "text": "Mr. PRESIDING JUSTICE EBERSPACHER\ndelivered the opinion of the court: ...",
                  "type": "majority"
              }
          ],
          "judges": [],
          "attorneys": [
              "John D. Shulleriberger, Morton Zwick, ...",
              "Robert H. Rice, State’s Attorney, of Belleville, for the Peop ..."
          ]
      }
    }

In this example, `"head_matter"` is a string representing all text printed in the volume before the text prepared by 
judges. `"opinions"` is an array containing a dictionary for each opinion in the case. `"judges"`, and 
`"attorneys"` are particular substrings from `"head_matter"` that we believe to refer to entities involved with the 
case.
      

XML Format
{: class="topic-header" }

[{% api_url "cases-list" %}?jurisdiction=ill&full_case=true&body_format=xml]({% api_url "cases-list" %}?jurisdiction=ill&full_case=true&body_format=xml)
{: class="example-link mt-0" }

The XML format is best if your analysis requires more information about pagination, formatting, or page layout. It 
contains a superset of the information available from body_format=text, but requires parsing XML data. Example 
response data:
      
    "data": "<?xml version='1.0' encoding='utf-8'?>\n<casebody ..."

HTML Format
{: class="topic-header" }

[{% api_url "cases-list" %}?jurisdiction=ill&full_case=true&body_format=html]({% api_url "cases-list" %}?jurisdiction=ill&full_case=true&body_format=html)
{: class="example-link mt-0" }

The HTML format is best if you want to show readable, formatted caselaw to humans. It represents a best-effort attempt 
to transform our XML-formatted data to semantic HTML ready for CSS formatting of your choice. Example response data:

    "data": "<section class=\"casebody\" data-firstpage=\"538\" data-lastpage=\"543\"> ..."


{# ====> PAGINATION <==== #}
# Pagination and Counts {: class="subtitle" data-toc-label='Pagination and Counts' }
  
Queries by default return 100 results per page, but you may request a smaller or larger number (up to 10,000!) using the
`page_size` parameter:
  
    curl "{% api_url "cases-list" %}?jurisdiction=ill&page_size=1"
  
We use [cursor](#def-cursor)-based pagination, meaning we keep track of where you are in the results set with a token, 
and you can access each page of results by returning the token included in the `"previous"` and `"next"` keys of the 
response:
  
    {
      "count": 183149,
      "next": "{% api_url "cases-list" %}?cursor=cD0xODMyLTEyLTAx",
      "previous": "{% api_url "cases-list" %}?cursor=bz0xMCZyPTEmcD0xODI4LTEyLTAx"
      ...
    }


{# ====> Searching and Filtering <==== #}
# Searching and Filtering Cases {: class="subtitle" data-toc-label='Search' }

Our [cases endpoint](#endpoint-cases) is indexed by Elasticsearch, and supports a range of searching, filtering, and
sorting options.

Options in this section work only with the cases endpoint.
{: class="highlighted" }

Full-text Search
{: #case-fts class="topic-header" }

Full-text search uses the `search` parameter. For example, if you'd
like to search for all cases that contain the word 'baronetcy', use the following query:

    {% api_url "cases-list" %}?search=baronetcy

The `search` field supports Elasticsearch [Simple Query String Syntax](https://www.elastic.co/guide/en/elasticsearch/reference/6.8/query-dsl-simple-query-string-query.html#_simple_query_string_syntax)
For example, you can use `"quotes"` to search by phrase and `-negation` to exclude cases with matching terms.

The `search` parameter searches the case, jurisdiction, and court names, docket number, and case text.
You can also use the `name`, `name_abbreviation`, or `docket_number` parameters to perform full-text search
just on those fields.

Filtering by Groups or Ranges
{: #case-filtering class="topic-header" }

Many of the parameters on the cases endpoint can be filtered by appending a suffix to the query parameter key.

To match to a list, append `__in` to the query parameter. For example, to fetch cases matching ID `12`, `34`, or `56`:

    curl "{% api_url "cases-list" %}?id__in=12__34__56"

To filter by less than or greater than, append `__gt` (greater than), `__gte` (greater than or equal to), 
`__lt` (less than), or `__lte` (less than or equal to). For example, to fetch cases of 2,000 to 3,000 words:

    curl "{% api_url "cases-list" %}?analysis.word_count__gte=2000&analysis.word_count__lte=3000"

To filter by prefix, append `__prefix`. For example, to find cases from February of 1800:

    curl "{% api_url "cases-list" %}?decision_date__prefix=1800-02"
    
Sorting
{: class="topic-header" }
  
You can sort your search in the cases endpoint using the `ordering` argument. To order your results in ascending order, 
supply the ordering argument with the field on which you'd like to sort your results. For example, if you'd like to 
search for the term 'baronetcy' with the oldest cases appearing first, supply the following query: 

    {% api_url "cases-list" %}?search=baronetcy&ordering=decision_date

You can also sort in descending order by adding a minus sign before the field on which you'd like to sort. To perform 
the same search sorted in descending order, that is, seeing the newest cases first, then use this query:

    {% api_url "cases-list" %}?search=baronetcy&ordering=-decision_date

{# ====> Analysis Fields <==== #}
# Analysis Fields {: class="subtitle" }

Each case result in the API returns an analysis section, such as:

    "analysis": {
        "word_count": 16593,
        "ocr_confidence": 0.691,
        "char_count": 92845,
        "page_rank": 0.1
    }

Analysis fields are values calculated by processing the raw case text. They can be searched with [filters](#case-filtering).

All analysis fields are optional, and may or may not appear for a given case.

Analysis fields have the following meanings:

Character count (`char_count`)
{: class="topic-header" }

The number of unicode characters in the full case text including headnotes.

OCR Confidence (`ocr_confidence`)
{: class="topic-header" }

A relative score of the predicted accuracy of optical character recognition in the case, from 0.0 to 1.0.
`ocr_confidence` is generated by averaging the OCR engine's reported confidence for each word in the case.
The score has no objective interpretation, other than that a case with a lower score is likely to have more
typographical errors than a case with a higher score.

PageRank (`pagerank`)
{: class="topic-header" }

Example: `"pagerank": {"raw": 0.00278, "percentile": 0.997}`

An estimate of the all-time significance of this case in the citation graph, from 0.0 to 1.0, calculated using
the PageRank algorithm. Cases with no inbound citations will not have this field, and implicitly have a rank of 0.

The `"raw"` score can be interpreted as the probability of encountering that case if you start at a random case and 
followed random citations. The `"percentile"` score indicates the percentage of cases, between 0.0 and 1.0, that have
a lower raw score than the given case. 

Word count (`word_count`)
{: class="topic-header" }

The number of words in the full case text including headnotes, defined as the number of character strings separated by
spaces.

{# ==============> ACCESS LIMITS <============== #}
# Access Limits {: class="subtitle" }
  
The agreement with our project partner, [Ravel](http://ravellaw.com), requires us to limit access to the full
text of cases to no more than 500 cases per person, per day. This limitation does not apply to 
[researchers](#def-researchers) who agree to certain restrictions on use and redistribution. Nor does this restriction 
apply to cases issued in [jurisdictions](#def-jurisdiction) that make their newly issued cases freely 
available online in an authoritative, citable, machine-readable format. We call these 
[whitelisted](#def-whitelisted) jurisdictions. Currently, Illinois, Arkansas, New Mexico, and North Carolina
are the only whitelisted jurisdictions.
  
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
{: class="mt-0" }


{# ==============> EXAMPLES <============== #}
# Usage Examples  {: class="subtitle" data-toc-label='Examples' }
  
This is a non-exhaustive set of examples intended to orient new users. The [endpoints](#endpoints) section contains more
comprehensive documentation about the URLs and their parameters.
  
{# ====> single case <==== #}
Retrieve a single case by ID
{: class="topic-header" }

[{% api_url "cases-detail" case.id %}]({% api_url "cases-detail" case.id %})
{: class="example-link mt-0" }

This example uses the [single case](#endpoint-case) endpoint, and will retrieve the metadata for a single 
case.


{# ====> filter cases <==== #}
Retrieve a list of cases using a metadata filter
{: class="topic-header" }

[{% api_url "cases-list" %}?cite={{ case.citations.0.cite }}]({% api_url "cases-list" %}?cite={{ case.citations.0.cite }})
{: class="example-link mt-0" }

This example uses the [cases](#endpoint-cases) endpoint, and will retrieve every case with the citation 
{{ case.citations.0.cite }}. 

There are many parameters with which you can filter the cases result. Check the 
[cases](#endpoint-cases) endpoint documentation for a complete list of the parameters, and what values they accept.

Modification with Parameters:
{: class="list-header mb-2" }

* **Add a date range filter**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "cases-list" %}?cite={{ case.citations.0.cite }}&decision_date_min=1900-12-30&decision_date_max=2000-12-30]({% api_url "cases-list" %}?cite={{ case.citations.0.cite }}&decision_date_min=1900-12-30&decision_date_max=2000-12-30)
    {: add_list_class="example-mod-url" }
    * You can combine any of these parameters to refine your search. Here, we have the same search as in the first 
    example, but will only receive results from within the specified dates.
    {: add_list_class="example-mod-description" }


{# ====> Full Text Search <==== #}
Full-Text Search
{: class="topic-header" }

[{% api_url "cases-list" %}?search=insurance]({% api_url "cases-list" %}?search=insurance)
{: class="example-link mt-0" }

This example performs a simple full-text case search which finds all cases containing the word "insurance." 

We support searching by phrase, exclusion, and some other full-text-search functionality. Check out our 
[search](#search) section for more information.

There are also many parameters with which you can filter the cases result. Check the [cases](#endpoint-cases) endpoint 
documentation for a complete list of the parameters, and what values they accept.

Modification with Parameters:
{: class="list-header mb-2" }

* **Add Search Term**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "cases-list" %}?search=insurance Peoria]({% api_url "cases-list" %}?search=insurance Peoria)
    {: add_list_class="example-mod-url" }
    * You can narrow your search results by adding terms, separated by spaces. This search will only include cases that contain both "insurance" and Peoria.
    {: add_list_class="example-mod-description" }
* **Filter Search With Metadata**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "cases-list" %}?search=insurance Peoria&jurisdiction=ill]({% api_url "cases-list" %}?search=insurance Peoria&jurisdiction=ill)
    {: add_list_class="example-mod-url" }
    * These queries can be filtered using other metadata fields. This query will perform the prior search while limiting
     the query to the Illinois jurisdiction.
    {: add_list_class="example-mod-description" }


{# ====> Get All Reporters <==== #}
Get all reporters in a jurisdiction
{: class="topic-header" }

[{% api_url "reporter-list" %}?jurisdictions=ark]({% api_url "reporter-list" %}?jurisdictions=ark)
{: class="example-link mt-0" }

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


{# ==============> CASES <============== #}
Case Browse/Search Endpoint
{: class="topic-header", id="endpoint-cases" }

[{% api_url "cases-list" %}]({% api_url "cases-list" %})
{: class="endpoint-link" style="margin-top: 0px;" }

This is the primary endpoint; you use it to browse, search for, and retrieve cases. If you know the numeric ID of your 
case in our system, you can append it to the [path](#def-path) to retrieve a [single case](#endpoint-case).

Endpoint Parameters:
{: class="list-header mb-2" }

Many parameters can be appended with `__in`, `__gt`, `__gte`, `__lt`, or `__lte`. See [Filtering](#case-filtering).

* `id` 
{: add_list_class="parameter-list" }
    * __data type:__    integer
* `name_abbreviation`
    * __data type:__    string
    * __description:__  e.g. `People v. Smith`
* `decision_date`
    * __data type:__    `YYYY-MM-DD` or a substring
* `last_updated`
    * __data type:__    `YYYY-MM-DDTHH:MM:SS` or a substring
* `docket_number`
    * __data type:__    string
    * __description:__  [full-text search](#case-fts)
* `cite`
    * __data type:__    string
    * __description:__  citation to case, e.g. `1 Ill. 21`
* `cites_to`
    * __data type:__    string or integer
    * __description:__  find cases that cite to the given citation or case ID, e.g. `1 Ill. 21` or `12345`
* `reporter`
    * __data type:__    integer
    * __description:__  [reporter](#endpoint-reporters) id
* `court`
    * __data type:__    [slug](#def-slug)
    * __description:__  [court](#endpoint-courts) slug
* `court_id`
    * __data type:__    integer
    * __description:__  [court](#endpoint-courts) id
* `jurisdiction`
    * __data type:__    [slug](#def-slug)
    * __description:__  [jurisdiction](#endpoint-jurisdictions) slug
* `search`
    * __data type:__    string
    * __description:__  [full-text search](#case-fts)
* `analysis.<key>`
    * __data type:__    integer or float
    * __description:__  Filter by an [analysis field](#analysis-fields), e.g. `analysis.word_count__gt=1000`
* `cursor`
    * __data type:__    string
    * __description:__  A value provided by a previous search result to go to the next page of results
* `ordering`
    * __data type:__    string
    * __description:__  A field name to sort your results in ascending order. Prepend with a minus 
    sign to sort in reverse order. See [Search](#search) for more details.
* `full_case`
    * __data type:__    "true" or "false"
    * __default:__      "false"
    * __description:__  When set to `true`, load the case body. Required when setting `body_format`.
* `body_format`
    * __data type:__    "text", "html", or "xml"
    * __default:__      "text"
    * __description:__  Change the case body format from JSON to html or xml.
            
            
{# ==============> CASE <============== #}
Single Case Endpoint
{: class="topic-header", id="endpoint-case" }

[{% api_url "cases-detail" case.id %}]({% api_url "cases-detail" case.id %})
{: class="endpoint-link" style="margin-top: 0px;" }

Use this endpoint to retrieve a single case.

Endpoint Parameters:
{: class="list-header mb-2" }

* `full_case` 
{: add_list_class="parameter-list" }
    * __data type:__    "true" or "false"
    * __default:__      "false"
    * __description:__  When set to `true`, load the case body. Required when setting `body_format`.
* `body_format`
    * __data type:__    "text", "html", or "xml"
    * __default:__      "text"
    * __description:__  Change the case body format from JSON to html or xml.


{# ==============> reporters <============== #}
Reporters Endpoint
{: class="topic-header", id="endpoint-reporters" }

[{% api_url "cases-list" %}]({% api_url "reporter-list" %}){: class="endpoint-link" }
{: class="endpoint-link" style="margin-top: 0px;" }

This will return a list of reporter series.

Endpoint Parameters:
{: class="list-header mb-2" }

* `full_name` 
{: add_list_class="parameter-list" }
    * __data type:__    string
    * __description:__  the full reporter name, e.g. Illinois Appellate Court Reports
* `short_name`
    * __data type:__    string
    * __description:__  the short reporter name, e.g. Ill. App.
* `start_year`
    * __data type:__    integer
    * __description:__  the earliest year reported on in the series
* `end_year`
    * __data type:__    integer
    * __description:__  the latest year reported on in the series
* `volume_count`
    * __data type:__    integer
    * __description:__  filter on the number of volumes in a reporter series
* `cursor`
    * __data type:__    string
    * __description:__  A value provided by a previous search result to go to the next page of results


{# ==============> jurisdictions <============== #}
Jurisdictions Endpoint
{: class="topic-header", id="endpoint-jurisdictions" }

[{% api_url "jurisdiction-list" %}]({% api_url "jurisdiction-list" %}){: class="endpoint-link"  }
{: class="endpoint-link" style="margin-top: 0px;" }

This will return a list of jurisdictions.
      
Endpoint Parameters:
{: class="list-header mb-2" }

* `name_long` 
{: add_list_class="parameter-list" }
    * __data type:__    string
    * __description:__  the full jurisdiction name, e.g. Illinois
* `name`
    * __data type:__    string
    * __description:__  the short jurisdiction name, e.g. Ill.
* `whitelisted`
    * __data type:__    "true" or "false"
    * __description:__  filter for [whitelisted](#def-whitelisted) jurisdictions
* `slug`
    * __data type:__    string
    * __description:__  filter on the jurisdiction [slug](#def-slug)
* `cursor`
    * __data type:__    string
    * __description:__  A value provided by a previous search result to go to the next page of results
    
{# ==============> courts <============== #}
Courts
{: class="topic-header", id="endpoint-courts" }

[{% api_url "court-list" %}]({% api_url "court-list" %}){: class="endpoint-link"  }
{: class="endpoint-link" style="margin-top: 0px;" }

This will return a list of courts.
      
Endpoint Parameters:
{: class="list-header mb-2" }

* `name_long` 
{: add_list_class="parameter-list" }
    * __data type:__    string
    * __description:__  the full court name, e.g. Illinois Appellate Court
* `name_abbreviation`
    * __data type:__    string
    * __description:__  the short jurisdiction name, e.g. Ill. App. Ct.
* `whitelisted`
    * __data type:__    "true" or "false"
    * __description:__  filter for [whitelisted](#def-whitelisted) jurisdictions
* `jurisdiction`
    * __data type:__    string
    * __description:__  filter on the jurisdiction [slug](#def-slug)
* `slug`
    * __data type:__    string
    * __description:__  filter on the court [slug](#def-slug)
* `cursor`
    * __data type:__    string
    * __description:__  A value provided by a previous search result to go to the next page of results


{# ==============> volumes <============== #}
Volumes
{: class="topic-header", id="endpoint-volumes" }

[{% api_url "volumemetadata-list" %}]({% api_url "volumemetadata-list" %}){: class="endpoint-link" }
{: class="endpoint-link" style="margin-top: 0px;" }

This will return a complete list of volumes.
      
Endpoint Parameters:
{: class="list-header mb-2" }

* `cursor` 
{: add_list_class="parameter-list" }
    * __data type:__    string
    * __description:__  A value provided by a previous search result to go to the next page of results

{# ==============> ngrams <============== #}
Ngrams
{: class="topic-header", id="endpoint-ngrams" }

[{% api_url "ngrams-list" %}]({% api_url "ngrams-list" %}){: class="endpoint-link" }
{: class="endpoint-link" style="margin-top: 0px;" }

For any given term, this endpoint returns a year-by-year list of:
{: class="mb-0" }

* the number of cases in which that term appears, and the total number of cases
* the number of times that term appears in all cases, and the total number of terms
{: add_list_class="bullets mt-0" }

If you set the optional `jurisdiction` parameter, your results will be limited to a specific jurisdiction.


Endpoint Parameters:
{: class="list-header mb-2" }

* `q` 
{: add_list_class="parameter-list" }
    * __data type:__    string
    * __description:__  Up to 3 space separated words. All words beyond the third are ignored.
* `jurisdiction`
    * __data type:__    string
    * __description:__  [Jurisdiction](#endpoint-jurisdiction) [slug](#def-slug): e.g. `tex` or `mass`.
        Limit your results to a specific jurisdiction.
* `year`
    * __data type:__    YYYY
    * __description:__  Filter results by year.

Here's the output when 
[querying for 'raisins' in California in 1984]({% api_url "ngrams-list" %}?q=raisins&jurisdiction=cal&year=1984): 

    {
        "count": 1,
        "next": null,
        "previous": null,
        "results": {
            "raisins": {
                "cal": [
                    {
                        "year": "1984",
                        "count": [
                            40,
                            4589927
                        ],
                        "doc_count": [
                            1,
                            1237
                        ]
                    }
                ]
            }
        }
    } 
    
Under `results` is an object containing the results for the query term `raisins`. Each jurisdiction's [slug](#def-slug) 
is a key in the `raisins` object. Only `cal` is listed because the jurisdiction parameter in the query is set to `cal`. 
Under `cal`, there is an array of objects, each containing the counts for a specific year. Since this query filters for 
results from 1984, that's the only year listed. Under `count`, there's `40, 4589927`, meaning *4,589,927* terms were 
indexed for California in 1984, and 40 of those are *raisins*. Under `doc_count` there's `1, 1237`, meaning *1,237* 
cases were indexed for California in 1984, and *raisins* shows up in *1* of those cases.
    
{# ==============> Citations <============== #}
Citations
{: class="topic-header", id="endpoint-citations" }

[{% api_url "extractedcitation-list" %}]({% api_url "extractedcitation-list" %}){: class="endpoint-link" }
{: class="endpoint-link" style="margin-top: 0px;" }

This will return a list of citations that cases have cited to.
      
Endpoint Parameters:
{: class="list-header mb-2" }

* `cursor` 
{: add_list_class="parameter-list" }
    * __data type:__    string
    * __description:__  A value provided by a previous search result to go to the next page of results

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
  
    https://www.google.com/search?q=CAP
  
Let's break it down into its individual parts:
  
    https://
  
This first part tells your web browser which protocol to use: this isn't very important for our purposes, so we'll 
ignore it.
  
    www.google.com
  
The next part is a list of words, separated by periods, between the initial double-slash, and before the subsequent 
single slash. Many people generically refer to this as the domain, which is only partly true, but the reason why that's 
not entirely true isn't really important for our purposes; the important consideration here is that it points to a 
specific [server](#def-server), which is just another computer on the internet. 

    /search
  
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
  
    ?q=CAP
  
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
[endpoints](#endpoints) and the parameters we've defined. Would you like to see how this works in a real application? 
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
* Special characters are characters that have programmatic significance to a program. The "specialness" of any given 
character is determined by the context in which it's used. For example, you can't add a bare question mark to your path 
because they indicate to the server that everything after them is a [parameter](#def-parameter).
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
* You can think of an endpoint as a distinct part of a program, which could require specific inputs, and/or provide 
different results. For example, the "login" endpoint on a website might accept a valid username and a password for 
input, and return a message that you've successfully logged in. A "register" endpoint might accept various bits of 
identifying information, and return a screen that says your account was successfully registered.
{: class="mt-1" }
  

* Jurisdiction
{: class="list-header mb-0" id="def-jurisdiction" }
* The jurisdiction of a case or volume is the political division it belongs to, such as the United States, a state, a 
territory, a tribe, or the District of Columbia. Volumes that collect cases from a region have the jurisdiction 
"Regional." Cases from tribal courts (other than Navajo Nation) temporarily have the jurisdiction "Tribal Jurisdictions"
while we verify the correct jurisdiction for each tribal court.
{: class="mt-1" }


* OCR
{: class="list-header mb-0" id="def-ocr" }
* OCR is a process in which a computer attempts to create text from an image of text. The text in our cases is 
OCR-derived using scanned case reporter pages as source images.
{: class="mt-1" }


* RESTful
{: class="list-header mb-0" id="def-restful" }
* A RESTful [API](#def-api) is based on [HTTP](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol), and makes use
of its built-in verbs(commands), such as GET and POST.
{: class="mt-1" }


* Reporter
{: class="list-header mb-0" id="def-reporter" }
* In this project, we use the term 'reporter' to refer to a reporter series. We'd consider F2d. a reporter.
{: class="mt-1" }


* Server
{: class="list-header mb-0" id="def-server" }
* A server is just a computer on the internet that was configured to respond to requests from other computers. A web 
server will respond to requests from a web browser. An email server will respond to requests from email programs, and or
other email servers which are sending it messages.
{: class="mt-1" }


* Slug
{: class="list-header mb-0" id="def-slug" }
* A [string](#def-string) with [special characters](#def-special-character) removed for ease of inclusion in a 
[url](#def-url).
{: class="mt-1" }


* String
{: class="list-header mb-0" id="def-string" }
* A string, as a type of data, just means an arbitrary list (or string) of [characters](#def-character). A word is a 
string. This whole sentence is a string. "h3ll0.!" is a string. This whole document is a string.
{: class="mt-1" }


* Top-Level Domain
{: class="list-header mb-0" id="def-tld" }
* The suffix to a domain name, such as `.com`, `.edu` or `.co.uk`.
{: class="mt-1" }


* URL
{: class="list-header mb-0" id="def-url" }
* A URL, or Uniform Resource Locator, is an internet address that generally contains a communication protocol, a server 
name, a path to a file or endpoint, and possibly parameters to pass to the endpoint.
{: class="mt-1" }


* URL Parameter
{: class="list-header mb-0" id="def-parameter" }
* For our purposes, a parameter is just a piece of data with a label that can be passed to an [endpoint](#def-endpoint) 
in a web request.
{: class="mt-1" }


* URL Path
{: class="list-header mb-0" id="def-path" }
* The URL path begins with the slash after the [top-level domain](#def-tld) and ends with the question mark that signals
 the beginning of the [parameters](#def-parameter). It was originally intended to point to a file on the server's hard 
 drive, but these days it's just as likely to point to an application [endpoint](#def-endpoint).
{: class="mt-1" }


* Whitelisted
{: class="list-header mb-0" id="def-whitelisted" }
* While most cases in the database are subject to a 500 case per day access limit, jurisdictions that publish their 
cases in a citable, machine-readable format are not subject to this limit. 
For more information on access limits, what type of users aren't subject to them, and how you can eliminate them in your
legal jurisdiction, visit our [access limits](#access-limits) section.
{: class="mt-1" }


* Cursor
{: class="list-header mb-0" id="def-cursor" }
* This property, populated with a random alphanumeric value, is present in all endpoints. It represents a specific page 
of results for a query. You can get the value of the cursor for the next and previous pages from the cursor parameter in
the urls in the `next` and `previous` fields.
{: class="mt-1" }


{# ==============> CHANGES AND STABILITY <============== #}
# Changes and Stability {: class="subtitle" data-toc-label='Stability'  }


This API is a work in progress. The format of the data it serves may change, and features will be added and possibly 
removed or replaced. If your work relies on access to specific data in a specific format, you should download the data 
and use local copies. If you have specific concerns about a particular feature of the API or future availability of 
specific data, [get in touch]({% url "contact" %}). To see what we've changed recently, check out our 
[changelog]({% url "changelog" %}).
