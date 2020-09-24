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
[API Browser]({% api_url "api-root" %}){: class="btn-primary" }

CAPAPI includes an in-browser API viewer, but is primarily intended for software developers to access caselaw 
programmatically, whether to run your own analysis or build tools for other users. API results are in JSON format with 
case text available as structured XML, presentation HTML, or plain text.

To get started with the API, you can [explore it in your browser]({% api_url "api-root" %}), or reach it from the 
command line. For example, here is a curl command to request a single case from Illinois:

    curl "{% api_url "cases-list" %}?jurisdiction=ill&page_size=1"

If you haven't used APIs before, you might want to check out our [search tool]({% url "search" %}) or jump down to our 
[Beginner's Introduction to APIs]({% url 'docs' 'tutorials_and_guides/intro_to_APIs' %}#beginners-introduction-to-apis).

{# ==============> REGISTER  <============== #}
# Registration {: class="subtitle" }

Most API queries don't require registration: check our [access limits](#access-limits) section for more details.
{: class="highlighted" }

[Click here to register for an API key]({% url "register" %}) if you need to access case text from 
non-[whitelisted]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-whitelisted) jurisdictions.

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

Sitewide Token Authentication
{: class="topic-header" }

In addition to using the `Authorization: Token abcd12345` header on API endpoints, you can use the same header to send
authenticated requests to any other page at case.law, such as the [Downloads]({% url "download-files" "" %}) section.
  

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
  
We use [cursor]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-cursor)-based pagination, meaning we keep track of where you are in the results set with a token, 
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

Cardinality (`cardinality`)
{: class="topic-header" }

The number of unique words in the full case text including head matter.

Character count (`char_count`)
{: class="topic-header" }

The number of unicode characters in the full case text including head matter.

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

SHA-256 (`sha256`)
{: class="topic-header" }

The hex-encoded SHA-256 hash of the full case text including head matter. This will match only if two cases
have identical text, and will change if case text is edited (such as for OCR correction).

SimHash (`simhash`)
{: class="topic-header" }

The hex-encoded, 64-bit [SimHash](https://en.wikipedia.org/wiki/SimHash) of the full case text including head matter.
The simhash of cases with more similar text will have lower Hamming distance. 

Simhashes are prepended by a version number, such as `"1:33e68120ecb2d7de"`, to allow for algorithmic improvements.
Simhashes with different version numbers may have been calculated using different parameters (such as hash algorithm
or tokenization) and may not be directly comparable.

Word count (`word_count`)
{: class="topic-header" }

The number of words in the full case text including head matter.

{# ==============> ACCESS LIMITS <============== #}
# Access Limits {: class="subtitle" }
  
The agreement with our project partner, [Ravel](http://ravellaw.com), requires us to limit access to the full
text of cases to no more than 500 cases per person, per day. This limitation does not apply to 
[researchers]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-researchers) who agree to certain restrictions on use and redistribution. Nor does this restriction 
apply to cases issued in [jurisdictions]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-jurisdiction) that make their newly issued cases freely 
available online in an authoritative, citable, machine-readable format. We call these 
[whitelisted]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-whitelisted) jurisdictions. Currently, Illinois, Arkansas, New Mexico, and North Carolina
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
* Unlimited API access to all cases from [whitelisted]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }
* Bulk Download all cases from [whitelisted]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }

Registered Users
{: class="topic-header", id="def-registered-user" }

* Access all metadata
{: class="list-group-item" add_list_class="parameter-list" }
* Unlimited API access to all cases from [whitelisted]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }
* Access to 500 cases per day from non-[whitelisted]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
{: class="list-group-item" add_list_class="parameter-list" }
* Bulk Download all cases from [whitelisted]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
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

This is the base [endpoint]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-endpoint) of 
CAPAPI. It just lists all of the available 
[endpoints]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-endpoint).


{# ==============> CASES <============== #}
Case Browse/Search Endpoint
{: class="topic-header", id="endpoint-cases" }

[{% api_url "cases-list" %}]({% api_url "cases-list" %})
{: class="endpoint-link" style="margin-top: 0px;" }

This is the primary endpoint; you use it to browse, search for, and retrieve cases. If you know the numeric ID of your 
case in our system, you can append it to the [path]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-path) to retrieve a [single case](#endpoint-case).

Endpoint Parameters:
{: class="list-header mb-2" }

Many parameters can be appended with `__in`, `__gt`, `__gte`, `__lt`, or `__lte`. See [Filtering](#case-filtering).

* `analysis.<key>`
{: add_list_class="parameter-list" }
    * __data type:__    integer or float
    * __description:__  Filter by an [analysis field](#analysis-fields), e.g. `analysis.word_count__gt=1000`
* `body_format`
    * __data type:__    "text", "html", or "xml"
    * __default:__      "text"
    * __description:__  Change the case body format from JSON to html or xml. Requires `full_case=true`.
* `cite`
    * __data type:__    string
    * __description:__  citation to case, e.g. `1 Ill. 21`
* `cites_to`
    * __data type:__    string or integer
    * __description:__  find cases that cite to the given citation or case ID, e.g. `1 Ill. 21` or `12345`
* `court`
    * __data type:__    [slug]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-slug)
    * __description:__  [court](#endpoint-courts) slug
* `court_id`
    * __data type:__    integer
    * __description:__  [court](#endpoint-courts) id
* `cursor`
    * __data type:__    string
    * __description:__  A value provided by a previous search result to go to the next page of results
* `decision_date`
    * __data type:__    `YYYY-MM-DD` or a substring
* `docket_number`
    * __data type:__    string
    * __description:__  [full-text search](#case-fts)
* `full_case`
    * __data type:__    "true" or "false"
    * __default:__      "false"
    * __description:__  When set to `true`, load the case body. Required when setting `body_format`.
* `id` 
    * __data type:__    integer
* `jurisdiction`
    * __data type:__    [slug]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-slug)
    * __description:__  [jurisdiction](#endpoint-jurisdictions) slug
* `last_updated`
    * __data type:__    `YYYY-MM-DDTHH:MM:SS` or a substring
* `name_abbreviation`
    * __data type:__    string
    * __description:__  e.g. `People v. Smith`
* `ordering`
    * __data type:__    string
    * __description:__  A field name to sort your results in ascending order. Prepend with a minus 
    sign to sort in reverse order. See [Search](#search) for more details.
* `reporter`
    * __data type:__    integer
    * __description:__  [reporter](#endpoint-reporters) id
* `search`
    * __data type:__    string
    * __description:__  [full-text search](#case-fts)
            
            
{# ==============> CASE <============== #}
Single Case Endpoint
{: class="topic-header", id="endpoint-case" }

[{% api_url "cases-detail" case.id %}]({% api_url "cases-detail" case.id %})
{: class="endpoint-link" style="margin-top: 0px;" }

Use this endpoint to retrieve a single case.

Endpoint Parameters:
{: class="list-header mb-2" }

* `body_format`
{: add_list_class="parameter-list" }
    * __data type:__    "text", "html", or "xml"
    * __default:__      "text"
    * __description:__  Change the case body format from JSON to html or xml. Requires `full_case=true`.
* `format`
    * __data type:__    blank or "pdf"
    * __description:__  If "pdf", return original PDF of the case instead of JSON. Requires `full_case=true`.
* `full_case` 
    * __data type:__    "true" or "false"
    * __default:__      "false"
    * __description:__  When set to `true`, load the case body. Required when setting `body_format`.


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
    * __description:__  filter for [whitelisted]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
* `slug`
    * __data type:__    string
    * __description:__  filter on the jurisdiction [slug]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-slug)
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
    * __description:__  filter for [whitelisted]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
* `jurisdiction`
    * __data type:__    string
    * __description:__  filter on the jurisdiction [slug]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-slug)
* `slug`
    * __data type:__    string
    * __description:__  filter on the court [slug]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-slug)
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
    * __description:__  [Jurisdiction](#endpoint-jurisdiction) [slug]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-slug): e.g. `tex` or `mass`.
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
    
Under `results` is an object containing the results for the query term `raisins`. Each jurisdiction's [slug]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-slug) 
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

For now, we're not accepting bug reports for [OCR]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-ocr) problems. While our data is good quality for OCR'd text, we
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




{# ==============> CHANGES AND STABILITY <============== #}
# Changes and Stability {: class="subtitle" data-toc-label='Stability'  }


This API is a work in progress. The format of the data it serves may change, and features will be added and possibly 
removed or replaced. If your work relies on access to specific data in a specific format, you should download the data 
and use local copies. If you have specific concerns about a particular feature of the API or future availability of 
specific data, [get in touch]({% url "contact" %}). To see what we've changed recently, check out our 
[changelog]({% url "changelog" %}).
