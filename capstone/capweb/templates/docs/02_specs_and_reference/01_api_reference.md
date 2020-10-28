{% load static %}
{% load pipeline %}
{% load api_url %}
title: API documentation
page_image: img/og_image/docs.png
meta_description: Caselaw Access Project API Docs
top_section_style: bg-black
row_style: bg-tan
explainer: The Caselaw Access Project API, also known as CAPAPI, serves all official US court cases published in books from 1658 to 2018. The collection includes over six million cases scanned from the Harvard Law School Library shelves. <a href="{% url "about" }>Learn more about the project</a>.



{# ==============> AUTHENTICATION <============== #}
# Authentication {: class="subtitle" }

Most API queries don't require registration: check our [access limits](#access-limits) section for more details.
{: class="highlighted" }

## Get an API Key
Before you can authenticate, you'll need an API key. 
* First [register]({% url 'docs' 'user_guides/registration' %}) an account.
* Log in
* Click on the "ACCOUNT" link at the top of the screen.
* The API Key is listed in your profile.

## Modify The Request Headers
To authenticate a request from the command line or a program, pass the `Authorization` header with your request. 
<span class="highlighted">The format of the `Authorization` header value is important: Use the string `Token` followed 
by a space, followed by your API key.</span> 

## Example

With an API key of `abcd12345`, you would pass `Token abcd12345` to the `Authorization` header.

A curl command would look like this:
  
    curl -H "Authorization: Token abcd12345" "{{ case_url }}?full_case=true"

In a program, (python's request library in this example,) it would look something like this:

    response = requests.get(
        '{{ case_url }}?full_case=true',
        headers={'Authorization': 'Token abcd12345'}
    )
  
## Failure: error_auth_required

In authentication fails, in the casebody object, you'll recieve 

         ...
          "casebody": {
            "data": null,
            "status": "error_auth_required"
          }
          ...

## Browsable API:

If you are [logged into this website]({% url "login" %}) and accessing the API through a web browser, all requests 
will be authenticated automatically.


In this example the response included a case from a non-whitelisted jurisdiction, and `casebody.data` for the case is 
therefore blank, while `casebody.status` is "error_auth_required".
  


## Sitewide Token Authentication

In addition to using the `Authorization: Token abcd12345` header on API endpoints, you can use the same header to send
authenticated requests to any other page at case.law, such as the [Downloads]({% url "download-files" "" %}) section.
  

{# ==============> DATA FORMATS <============== #}
# Case Text Formats
  
See [Data Specs]({% url 'docs' 'specs_and_reference/data_specs' %}).


{# ====> PAGINATION <==== #}
# Pagination and Counts {: class="subtitle" data-toc-label='Pagination and Counts' }

We use [cursor]({% url 'docs' 'user_guides/documentation_glossary' %}#def-cursor)-based pagination, meaning we 
keep track of where you are in the results set with a token, and you can access each page of results by returning the 
token included in the `"previous"` and `"next"` keys of the response.

Queries by default return 100 results per page, but you may request a smaller or larger number (up to 10,000!) using the
`page_size` parameter:
  
## Example
    curl "{% api_url "cases-list" %}?jurisdiction=ill&page_size=1"
  

    {
      "count": 183149,
      "next": "{% api_url "cases-list" %}?cursor=cD0xODMyLTEyLTAx",
      "previous": "{% api_url "cases-list" %}?cursor=bz0xMCZyPTEmcD0xODI4LTEyLTAx"
      ...
    }


{# ====> Analysis Fields <==== #}
# Analysis Fields {: class="subtitle" }

See [Data Specs]({% url 'docs' 'specs_and_reference/data_specs' %}).

{# ==============> ENDPOINTS <============== #}
# Endpoints {: class="subtitle" }

{# ==============> BASE <============== #}
API Base
{: class="topic-header", id="endpoint-base" }

[{% api_url "api-root" %}]({% api_url "api-root" %})
{: class="endpoint-link" style="margin-top: 0px;" }

This is the base [endpoint]({% url 'docs' 'user_guides/documentation_glossary' %}#def-endpoint) of 
CAPAPI. It just lists all of the available 
[endpoints]({% url 'docs' 'user_guides/documentation_glossary' %}#def-endpoint).


{# ==============> CASES <============== #}
Case Browse/Search Endpoint
{: class="topic-header", id="endpoint-cases" }

[{% api_url "cases-list" %}]({% api_url "cases-list" %})
{: class="endpoint-link" style="margin-top: 0px;" }

This is the primary endpoint; you use it to browse, search for, and retrieve cases. If you know the numeric ID of your 
case in our system, you can append it to the [path]({% url 'docs' 'user_guides/documentation_glossary' %}#def-path) to retrieve a [single case](#endpoint-case).

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
    * __data type:__    [slug]({% url 'docs' 'user_guides/documentation_glossary' %}#def-slug)
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
    * __data type:__    [slug]({% url 'docs' 'user_guides/documentation_glossary' %}#def-slug)
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

## Search Syntax

The `search` field supports Elasticsearch [Simple Query String Syntax](https://www.elastic.co/guide/en/elasticsearch/reference/6.8/query-dsl-simple-query-string-query.html#_simple_query_string_syntax)
For example, you can use `"quotes"` to search by phrase and `-negation` to exclude cases with matching terms.

## Examples

{# ====> filter cases <==== #}
Retrieve a list of cases using a metadata filter
{: class="topic-header" }

[{% api_url "cases-list" %}?cite={{ case_cite }}]({% api_url "cases-list" %}?cite={{ case_cite }})
{: class="example-link mt-0" }

Modification with Parameters:
{: class="list-header mb-2" }

* **Add a date range filter**
{: class="list-group-item" add_list_class="parameter-list" }
    * [{% api_url "cases-list" %}?cite={{ case_cite }}&decision_date_min=1900-12-30&decision_date_max=2000-12-30]({% api_url "cases-list" %}?cite={{ case_cite }}&decision_date_min=1900-12-30&decision_date_max=2000-12-30)
    {: add_list_class="example-mod-url" }
    * You can combine any of these parameters to refine your search. Here, we have the same search as in the first 
    example, but will only receive results from within the specified dates.
    {: add_list_class="example-mod-description" }


[{% api_url "cases-list" %}?search=insurance]({% api_url "cases-list" %}?search=insurance)
{: class="example-link mt-0" }

This example performs a simple full-text case search which finds all cases containing the word "insurance." 

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


{# ==============> CASE <============== #}
Single Case Endpoint
{: class="topic-header", id="endpoint-case" }

[{{ case_url }}]({{ case_url }})
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

## Example
  
Retrieve a single case by ID
{: class="topic-header" }

[{{ case_url }}]({{ case_url }})
{: class="example-link mt-0" }

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

## Examples
Get all reporters in a jurisdiction:

[{% api_url "reporter-list" %}?jurisdictions=ark]({% api_url "reporter-list" %}?jurisdictions=ark)
{: class="example-link mt-0" }

This example will retrieve all reporters in Arkansas.

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
    * __description:__  filter for [whitelisted]({% url 'docs' 'user_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
* `slug`
    * __data type:__    string
    * __description:__  filter on the jurisdiction [slug]({% url 'docs' 'user_guides/documentation_glossary' %}#def-slug)
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
    * __description:__  filter for [whitelisted]({% url 'docs' 'user_guides/documentation_glossary' %}#def-whitelisted) jurisdictions
* `jurisdiction`
    * __data type:__    string
    * __description:__  filter on the jurisdiction [slug]({% url 'docs' 'user_guides/documentation_glossary' %}#def-slug)
* `slug`
    * __data type:__    string
    * __description:__  filter on the court [slug]({% url 'docs' 'user_guides/documentation_glossary' %}#def-slug)
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
    * __description:__  [Jurisdiction](#endpoint-jurisdiction) [slug]({% url 'docs' 'user_guides/documentation_glossary' %}#def-slug): e.g. `tex` or `mass`.
        Limit your results to a specific jurisdiction.
* `year`
    * __data type:__    YYYY
    * __description:__  Filter results by year.

## Example

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
    
Under `results` is an object containing the results for the query term `raisins`. Each jurisdiction's [slug]({% url 'docs' 'user_guides/documentation_glossary' %}#def-slug) 
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

