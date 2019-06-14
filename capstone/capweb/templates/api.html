{% extends "layouts/full.html" %}
{% load static %}
{% load pipeline %}
{% load api_url %}

{% block extra_head %}
  {% stylesheet 'docs' %}
{% endblock %}

{% block title %}API documentation{% endblock %}
{% block meta_description %}Caselaw Access Project API Docs{% endblock %}
{% block top_section_style %}bg-black{% endblock %}
{% block row_style %}bg-tan{% endblock %}


{% block explainer %}
  The Caselaw Access Project API, also known as CAPAPI, serves all official US court cases
  published in books from 1658 to 2018. The collection includes over six million cases scanned from
  the Harvard Law Library shelves.
  <a href="{% url "about" %}">Learn more about the project.</a>
{% endblock %}

{% block sidebar_menu_items %}
  <li>
    <a class="list-group-item" href="#getting-started">
      <span class="text">Start Here</span>
    </a>
  </li>
  <li>
    <a class="list-group-item" href="#registration">
      <span class="text">Registration</span>
    </a>
  </li>
  <li>
    <a class="list-group-item" href="#authentication">
      <span class="text">Authentication</span>
    </a>
  </li>
  <li>
    <a class="list-group-item" href="#dataformats">
      <span class="text">Data Formats</span>
    </a>
  </li>
  <li>
    <a class="list-group-item" href="#pagination">
      <span class="text">Pagination and Counts</span>
    </a>
  </li>
  <li>
    <a class="list-group-item" href="#limits">
      <span class="text">Access Limits</span>
    </a>
  </li>
  <li>
    <a class="list-group-item" href="#examples">
      <span class="text">Examples</span>
    </a>
  </li>
  <li>
    <a class="list-group-item" href="#endpoints">
      <span class="text">Endpoints</span>
    </a>
  </li>
  <li>
    <a class="list-group-item" href="#beginners">
      <span class="text">Intro to APIs</span>
    </a>
  </li>
  <li>
    <a class="list-group-item" href="#problems">
      <span class="text">Report Issues</span>
    </a>
  </li>
  <li>
    <a class="list-group-item" href="#glossary">
      <span class="text">Glossary</span>
    </a>
  </li>
{% endblock %}

{% block main_content %}
  {# ==============> GETTING STARTED <============== #}
  <h2 class="subtitle" id="getting-started">Getting Started</h2>
  <p><a class="btn-primary" href="{% api_url "api-root" %}">API</a></p>
  <p>
    CAPAPI includes an in-browser API viewer, but is primarily intended for software developers to access
    caselaw programmatically, whether to run your own analysis or build tools for other users. API results are in JSON
    format with case text available as structured XML, presentation HTML, or plain text.
  </p>
  <p>
    To get started with the API, you can <a href="{% api_url "api-root" %}">explore it in your browser,</a>
    or reach it from the command line. For example, here is a curl command to request a single case from Illinois:</p>
  <pre class="code-block">curl "{% api_url "casemetadata-list" %}?jurisdiction=ill&page_size=1"</pre>
  <p>
    If you haven't used APIs before, you might want to check out our <a href="{% url "search" %}">search tool</a>,
    or jump down to our <a href="#beginners">Beginner's Introduction to APIs</a>.
  </p>

  {# ==============> REGISTER  <============== #}
  <h2 class="subtitle" id="registration">Registration</h2>
    <p>
      <span class="highlighted"> Most API queries don't require registration: check our
      <a href="#limits">access limits</a> section for more details.
      </span>
    </p>
  <p>
    <a href="{% url "register" %}">Click here to register for an API key</a> if you need to access case text
    from non-<a href="#def-whitelisted">whitelisted</a> jurisdictions.
  </p>

  {# ==============> AUTHENTICATION <============== #}
  <h2 class="subtitle" id="authentication">Authentication</h2>
  <p>
      <span class="highlighted"> Most API queries don't require registration: check our
        <a href="#limits">access limits</a> section for more details.
      </span>
  </p>
  <p>
    Most API requests do not need to be authenticated. However, if requests are not authenticated, you may see
    this response in results from the case endpoint with <code>full_case=true</code>:
  </p>
  <pre class="code-block">
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
}</pre>
  <p>
    In this example the response included a case from a non-whitelisted jurisdiction, and
    <code>casebody.data</code> for the case is therefore blank, while <code>casebody.status</code> is
    "error_auth_required".
  </p>
  <p>
    To authenticate the request from code or the command line, you can provide an <code>Authorization</code>
    header:
  </p>

  <pre class="code-block">curl -H "Authorization: Token abcd12345" "{% api_url "casemetadata-list" %}?full_case=true"</pre>
  <p>
    While you are <a href="{% url "login" %}">logged into this website</a>, all requests through the API
    browser will be authenticated automatically.
  </p>

  {# ==============> DATA FORMATS <============== #}
  <h2 class="subtitle" id="dataformats">Case Text Formats</h2>
  <p>
    <span class="highlighted">Both of these parameters must be used in conjunction with the
    <code>full_case=true</code>parameter.</span>
  </p>
  <p>
    CAPAPI is capable of returning case text in three formats: text(default), XML, or HTML. In most instances, each
    case is represented by a JSON object which includes various pieces of metadata, and the case text itself which is
    located in the <code>casebody</code> property. In both the <a href="#endpoint-cases"> case browse/search results
    endpoint</a> and the <a href="#endpoint-cases"> individual case endpoint</a>, the <code>casebody</code> parameter
    returns JSON structured plain text, but you can change that to either HTML or XML by setting the
    <code>body_format</code> query parameter to either <code>html</code> or <code>xml</code>.
  </p>
  <p>
    In the individual <a href="#endpoint-cases">case</a> endpoint, you can alternately pass <code>html</code> or
    <code>xml</code> to the <code>format</code> parameter to dispense with the JSON container and return only the
    HTML or XML formatted case. The HTML returned using the <code>format</code> parameter is the same as the HTML
    returned in the JSON container with <code>body_format</code> set to <code>html</code>. The XML output is
    significantly more verbose&mdash; It includes METS, PREMIS and structural metadata.
  </p>
  <p>
    Do not set both <code>format</code> and <code>body_format</code> in the same query, and always use them with the
    <code>full_case</code> parameter set to <code>true</code>. Using the <code>format</code> parameter with the
    <a href="#endpoint-cases"> case browse/search results endpoint</a> will have no effect.
  </p>
  <p>
  This is what you can expect from different format specifications using the <code>body_format</code>
  parameter.
  </p>
  <dl>
    <dt>Text Format (default)</dt>
    <dd class="example-link">
      <a href="{% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true">
      {% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true
      </a>
    </dd>
    <dd>
      <p>
        The default text format is best for natural language processing. Example response data:
      </p>
      <pre class="code-block">
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
      "parties": [
          "The People of the State of Illinois, Plaintiff-Appellee, v. Danny Tobin, Defendant-Appellant."
      ],
      "attorneys": [
          "John D. Shulleriberger, Morton Zwick, ...",
          "Robert H. Rice, State’s Attorney, of Belleville, for the Peop ..."
      ]
  }
}</pre>
      <p>
        In this example, <code>"head_matter"</code> is a string representing all text printed in the volume before
        the text prepared by judges. <code>"opinions"</code> is an array containing a dictionary for each opinion
        in the case. <code>"judges"</code>, <code>"parties"</code>, and <code>"attorneys"</code> are
        particular substrings from <code>"head_matter"</code> that we believe to refer to entities involved with the case.
      </p>
    </dd>

    <dt>XML Format</dt>
      <dd class="example-link">
        <a href="{% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true&body_format=xml" %}">
        {% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true&body_format=xml"
      </a>
    </dd>
    <dd>
      <p>
        The XML format is best if your analysis requires more information about pagination, formatting, or
        page layout. It contains a superset of the information available from body_format=text, but requires
        parsing XML data. Example response data:
      </p>
      <pre class="code-block">{% filter force_escape %}
"data": "<?xml version='1.0' encoding='utf-8'?>\n<casebody ..."{% endfilter %}</pre>
    </dd>

    <dt>HTML Format</dt>
    <dd class="example-link">
      <a href="{% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true&body_format=html">
      {% api_url "casemetadata-list" %}?jurisdiction=ill&full_case=true&body_format=html"
      </a></dd>
    <dd>
      <p>
        The HTML format is best if you want to show readable, formatted caselaw to humans. It represents a
        best-effort attempt to transform our XML-formatted data to semantic HTML ready for CSS formatting of your
        choice. Example response data:
      </p>
      <pre class="code-block">{% filter force_escape %}
"data": "<section class=\"casebody\" data-firstpage=\"538\" data-lastpage=\"543\"> ..."{% endfilter %}</pre>
    </dd>
  </dl>

  {# ====> PAGINATION <==== #}
  <h2 class="subtitle" id="pagination">Pagination and Counts</h2>
  <p>
    Queries by default return 100 results per page, but you may request a smaller number using the
    <code>page_size</code> parameter:
  </p>
  <pre class="code-block">curl "{% api_url "casemetadata-list" %}?jurisdiction=ill&page_size=1"</pre>
  <p>
    We use <a href="#def-cursor">cursor</a>-based pagination, meaning we keep track of where you are in the
    results set on the server, and you can access each page of results by using the link in the
    <code>"previous"</code> and <code>"next"</code> keys of the response:
  </p>
  <pre class="code-block">{% filter force_escape %}
{
  "count": 183149,
  "next": "{% api_url "casemetadata-list" %}?cursor=cD0xODMyLTEyLTAx",
  "previous": "{% api_url "casemetadata-list" %}?cursor=bz0xMCZyPTEmcD0xODI4LTEyLTAx"
  ...
}{% endfilter %}</pre>
  <p>
    Responses also include a <code>"count"</code> key. Occasionally this may show <code>"count": null</code>,
    indicating that the total count for a particular query has not yet been calculated.
  </p>

  {# ==============> ACCESS LIMITS <============== #}
  <h2 class="subtitle" id="limits">Access Limits</h2>
  <p>
    The agreement with our project partner, <a href="http://ravellaw.com">Ravel</a>, requires us to limit
    access to the full text of cases to no more than 500 cases per person, per day. This limitation does not
    apply to <a href="#def-researchers">researchers</a> who agree to certain restrictions on use and redistribution.
    Nor does this restriction apply to cases issued in <a href="#def-jurisdiction">jurisdictions</a> that make
    their newly issued cases freely available online in an authoritative, citable, machine-readable format. We call
    these <a href="#def-whitelisted">whitelisted</a> jurisdictions. Currently, Illinois and Arkansas are the
    only whitelisted jurisdictions.
  </p>
  <p>
    We would love to whitelist more jurisdictions! If you are involved in US case publishing at the state or federal
    level, we'd love to talk to you about making the transition to digital-first publishing. Please
    <a href="{% url "contact" %}">contact us</a> and introduce yourself!
  </p>
  <p>
    If you qualify for unlimited access as a research scholar, you can request a research agreement by
    <a href="{% url "register" %}">creating an account</a>
    and then <a href="{% url "user-details" %}">visiting your account page</a>.
  </p>
  <p>
    In addition, under our agreement with Ravel (now owned by Lexis-Nexis), Ravel must negotiate in good faith
    to provide bulk access to anyone seeking to make commercial use of this data.
    <a href="http://info.ravellaw.com/contact-us-form">Click here to contact Ravel for more information</a>,
    or <a href="{% url "contact" %}">contact us</a> and we will put you in touch with Ravel.
  </p>
  <dl>
    <dt>
      <a id="def-unregistered-user"></a>
      Unregistered Users
    </dt>
    <dd>
      <ul>
        <li class="list-group-item">Access all metadata</li>
        <li class="list-group-item">Unlimited API access to all cases from
          <a href="#def-whitelisted">whitelisted</a> jurisdictions
        </li>
        <li class="list-group-item">Bulk Download all cases from
          <a href="#def-whitelisted">whitelisted</a> jurisdictions
        </li>
      </ul>
    </dd>

    <dt>
      <a id="def-registered-user"></a>
      Registered Users
    </dt>
    <dd>
      <ul>
        <li class="list-group-item">Access all metadata</li>
        <li class="list-group-item">Unlimited API access to all cases from
          <a href="#def-whitelisted">whitelisted</a> jurisdictions
        </li>
        <li class="list-group-item">Access to 500 cases per day from non-<a
            href="#def-whitelisted">whitelisted</a> jurisdictions
        </li>
        <li class="list-group-item">Bulk Download all cases from
          <a href="#def-whitelisted">whitelisted</a> jurisdictions
        </li>
      </ul>
    </dd>

    <dt>
      <a id="def-researchers"></a>
      Researchers
    </dt>
    <dd>
      <ul>
        <li class="list-group-item">Access all metadata</li>
        <li class="list-group-item">Unlimited API access to all cases</li>
        <li class="list-group-item">Bulk Downloads from all jurisdictions</li>
      </ul>
    </dd>

    <dt>
      <a id="def-commerical-user"></a>
      Commercial Users
    </dt>
    <dd>
      <a href="http://info.ravellaw.com/contact-us-form">Click here to contact Ravel for more
        information.</a>
    </dd>
  </dl>

  {# ==============> EXAMPLES <============== #}
  <h2 class="subtitle" id="examples">
    Usage Examples
  </h2>
  <p>
    This is a non-exhaustive set of examples intended to orient new users. The
    <a href="#endpoints">endpoints</a> section contains more comprehensive documentation about the URLs and
    their parameters.
  </p>
  <dl>
    {# ====> single case <==== #}
    <dt>
      Retrieve a single case by ID
    </dt>
    <dd class="example-link">
      <a href="{% api_url "casemetadata-detail" case_id %}">
        {% api_url "casemetadata-detail" case_id %}</a>
    </dd>
    <dd>
      <p>
        This example uses the <a href="#endpoint-case">single case</a> endpoint, and will retrieve the
        metadata for a single case.
      </p>
      <h5 class="list-header">Modification with Parameters:</h5>
      <ul class="parameter-list">
        <li class="list-group-item">
          <h5 class="list-header">Standalone HTML-formatted Case</h5>
          <ul>
            <li class="example-mod-url"><a href="{% api_url "casemetadata-detail" case_id %}?full_case=true&format=html">
              {% api_url "casemetadata-detail" case_id %}?full_case=true&format=html</a>
            </li>
            <li class="example-mod-description">This will return a lightly styled, standalone HTML
              representation of the case with no accompanying metadata.
            </li>
          </ul>
        </li>
      </ul>
      <ul class="parameter-list">
        <li class="list-group-item">
          <h5 class="list-header">Plain Text Case in JSON container with metadata</h5>
          <ul>
            <li class="example-mod-url"><a href="{% api_url "casemetadata-detail" case_id %}">
              {% api_url "casemetadata-detail" case_id %}</a>
            </li>
            <li class="example-mod-description">This will return a lightly styled, standalone HTML
              representation of the case with no accompanying metadata.
            </li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header">Raw original XML document, with METS data</h5>
          <ul>
            <li class="example-mod-url">
              <a href="{% api_url "casemetadata-detail" case_id %}?full_case=true&body_format=xml">
                {% api_url "casemetadata-detail" case_id %}?full_case=true&format=xml
              </a>
            </li>
            <li class="example-mod-description">To get the document by itself, without the JSON enclosure and
              metadata, use the <code>format</code> parameter. Set it to HTML and get a display-ready,
              standalone HTML document.
            </li>
          </ul>
        </li>
      </ul>
    </dd>
    {# ====> filter cases <==== #}

    <dt>
      Retrieve a list of cases using a metadata filter
    </dt>
    <dd class="example-link">
      <a href="{% api_url "casemetadata-list" %}?cite={{ case_metadata.citations.0.cite }}">
        {% api_url "casemetadata-list" %}?cite={{ case_metadata.citations.0.cite }}
      </a>
    </dd>
    <dd>
      <p>
        This example uses the <a href="#endpoint-cases">cases</a> endpoint, and will retrieve every case with
        the citation {{ case_metadata.citations.0.cite }}.
      </p>
      <p>
        There are many parameters with which you can filter the cases result. Check the
        <a href="#endpoint-cases">cases</a> endpoint documentation for a complete list of the parameters, and
        what values they accept.
      </p>
      <h5 class="list-header">Modification with Parameters:</h5>
      <ul class="parameter-list">
        <li class="list-group-item">
          <h5 class="list-header">Add a date range filter</h5>
          <ul>
            <li class="example-mod-url">
              <a href="{% api_url "casemetadata-list" %}?cite={{ case_metadata.citations.0.cite }}&decision_date_min=1900-12-30&decision_date_max=2000-12-30">
                {% api_url "casemetadata-list" %}?cite={{ case_metadata.citations.0.cite }}&decision_date_min=1900-12-30&decision_date_max=2000-06-15
              </a>
            </li>
            <li class="example-mod-description">You can combine any of these parameters to refine your search.
              Here, we have the same search as in the first example, but will only receive results from within
              the specified dates.
            </li>
          </ul>
        </li>
      </ul>
    </dd>
  </dl>
  <dl>
    {# ====> filter cases <==== #}
    <dt>
      Simple Full-Text Search
    </dt>
    <dd class="example-link">
      <a href="{% api_url "casemetadata-list" %}?search=insurance">
        {% api_url "casemetadata-list" %}?search=insurance
      </a>
    </dd>
    <dd>
      <p>
        This example performs a simple full-text case search which finds all cases containing the word
        "insurance."
      </p>
      <p>
        There are many parameters with which you can filter the cases result. Check the
        <a href="#endpoint-cases">cases</a> endpoint documentation for a complete list of the parameters, and
        what values they accept.
      </p>
      <h5 class="list-header">Modification with Parameters:</h5>
      <ul class="parameter-list">
        <li class="list-group-item">
          <h5 class="list-header">Add Search Term</h5>
          <ul>
            <li class="example-mod-url">
              <a href="{% api_url "casemetadata-list" %}?search=insurance Peoria">
                {% api_url "casemetadata-list" %}?search=insurance Peoria
              </a>
            </li>
            <li class="example-mod-description">You can narrow your search results by adding terms, separated
              by spaces. This search will only include cases that contain both "insurance" and Peoria.
            </li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header">Filter Search With Metadata</h5>
          <ul>
            <li class="example-mod-url">
              <a href="{% api_url "casemetadata-list" %}?search=insurance Peoria&jurisdiction=ill">
                {% api_url "casemetadata-list" %}?search=insurance Peoria&jurisdiction=ill
              </a>
            </li>
            <li class="example-mod-description">These queries can be filtered using other metadata fields.
              This query will perform the prior search while limiting the query to the Illinois jurisdiction.
            </li>
          </ul>
        </li>
      </ul>
    </dd>
  </dl>


  {# ====> get reporters for a jurisdiction <==== #}
  <dl>
    <dt>
      Get all reporters in a jurisdiction
    </dt>
    <dd class="example-link">
      <a href="{% api_url "reporter-list" %}?jurisdictions=ark">
        {% api_url "reporter-list" %}?jurisdictions=ark
      </a>
    </dd>
    <dd>
      <p>
        This example uses the <a href="#endpoint-reporters">reporter</a> endpoint, and will retrieve all
        reporters in Arkansas.
      </p>
    </dd>
  </dl>

  {# ==============> ENDPOINTS <============== #}
  <h2 class="subtitle" id="endpoints">
    Endpoints
  </h2>
  <dl>

    {# ==============> BASE <============== #}
    <a id="endpoint-base"></a>
    <dt>
      API Base
    </dt>
    <dd class="endpoint-link">
      <a class="endpoint-link" href="{% api_url "api-root" %}">{% api_url "api-root" %}v1/</a>
    </dd>
    <dd>
      <p class="endpoint-description">
        This is the base <a href="#def-endpoint">endpoint</a> of CAPAPI. It just lists all of the available
        <a href="#def-endpoint">endpoints</a>.
      </p>
    </dd>

    {# ==============> CASES <============== #}
    <dt>
      <a id="endpoint-cases"></a>
      Case Browse/Search Endpoint
    </dt>
    <dd class="endpoint-link">
      <a href="{% api_url "casemetadata-list" %}">{% api_url "casemetadata-list" %}</a>
    </dd>
    <dd>
      <p class="endpoint-description">
        This is the primary endpoint; you use it to browse, search for, and retrieve cases. If you know the
        numeric ID of your case in our system, you can append it to the <a href="#def-path">path</a> to
        retrieve a <a href="#endpoint-case">single case</a>.
      </p>
      <h5 class="list-header">Endpoint Parameters:</h5>
      <ul class="parameter-list">
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">name_abbreviation</code></h5>
          <ul>
            <li class="param-data-type"> An arbitrary <a href="#def-string">string</a></li>
            <li class="param-description"> e.g. <code>People v. Smith</code></li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">decision_date_min</code></h5>
          <ul>
            <li class="param-data-type"><code>YYYY-MM-DD</code></li>
            <li class="param-description"></li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">decision_date_max</code></h5>
          <ul>
            <li class="param-data-type"><code>YYYY-MM-DD</code></li>
            <li class="param-description"></li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">docket_number</code></h5>
          <ul>
            <li class="param-data-type"> An arbitrary <a href="#def-string">string</a></li>
            <li class="param-description"></li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">citation</code></h5>
          <ul>
            <li class="param-data-type"> e.g. <code>1 Ill. 21</code></li>
            <li class="param-description"></li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">reporter</code></h5>
          <ul>
            <li class="param-data-type"> integer</li>
            <li class="param-description"> a <a href="#endpoint-reporters">reporter</a> id</li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">court</code></h5>
          <ul>
            <li class="param-data-type"><a href="#def-slug">slug</a></li>
            <li class="param-description"> a <a href="#endpoint-courts">court</a> <a href="#def-slug">slug</a>
            </li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">court_id</code></h5>
          <ul>
            <li class="param-data-type">integer</li>
            <li class="param-description"> a <a href="#endpoint-courts">court</a> id</li>
            </li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">jurisdiction</code></h5>
          <ul>
            <li class="param-data-type"><a href="#def-slug">slug</a></li>
            <li class="param-description"> a <a href="#endpoint-jurisdictions">jurisdiction</a> <a
                href="#def-slug">slug</a></li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">search</code></h5>
          <ul>
            <li class="param-data-type"> An arbitrary <a href="#def-string">string</a></li>
            <li class="param-description"> A full-text search query</li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 id="def-cursor" class="list-header"><code class="parameter-name">cursor</code></h5>
          <ul>
            <li class="param-data-type"> An randomly generated <a href="#def-string">string</a></li>
            <li class="param-description">
              This field contains a value that we generate which will bring you to a specific page of results.
            </li>
          </ul>
        </li>
      </ul>


    </dd>

    {# ==============> CASE <============== #}
    <dt>
      <a id="endpoint-case"></a>
      Single Case Endpoint
    </dt>
    <dd class="endpoint-link">
      <a href="{% api_url "casemetadata-detail" case_id %}">{% api_url "casemetadata-detail" case_id %}</a>
    </dd>
    <dd>
      <p class="endpoint-description">
        This is the way to retrieve a single case.
      </p>
      <h5 class="list-header">Endpoint Parameters:</h5>
      <ul class="parameter-list">
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">full_case</code></h5>
          <ul>
            <li class="param-data-type"><code>true</code> or <code>false</code></li>
            <li class="param-description">
              When set to <code>true</code>, this parameter loads the case body.
              It is required for setting both <code>body_format</code> and <code>format</code>.
            </li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">body_format</code></h5>
          <ul>
            <li class="param-data-type"><code>html</code> or <code>xml</code></li>
            <li class="param-description">
              This will return a JSON enclosure with metadata, and a field containing the case in XML or HTML.
            </li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">format</code></h5>
          <ul>
            <li class="param-data-type"><code>html</code> or <code>xml</code></li>
            <li class="param-description">
              This will return the case in HTML or its original XML with no JSON enclosure or metadata.
            </li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">cursor</code></h5>
          <ul>
            <li class="param-data-type"> An randomly generated <a href="#def-string">string</a></li>
            <li class="param-description">
              This field contains a value that we generate which will bring you to a specific page of results.
            </li>
          </ul>
        </li>
      </ul>
    </dd>
    <p>
      Here's what you can expect when you request a single case. Everything under
      <code><span class="code-example-casebody-section">casebody</span></code> is only returned if
      <code>full_case=true</code> is set. In the <a href="#endpoint-cases">cases</a> endpoint, you'd get a
      list of these in a JSON object which also included pagination information and result counts.
    </p>
    <pre class="code-block">{
  "id": <span class="json-data-type">integer</span>
  "url": <span class="json-data-type"><a href="#def-url">url</a></span>,
  "name": <span class="json-data-type"><a href="#def-string">string</a></span>,
  "name_abbreviation": <span class="json-data-type"><a href="#def-string">string</a></span>,
  "decision_date": <span class="json-data-type">YYYY-MM-DD</span>,
  "docket_number": <span class="json-data-type"><a href="#def-string">string</a></span>,
  "first_page": <span class="json-data-type"><a href="#def-string">string</a> (generally a number)</span>,
  "last_page": <span class="json-data-type"><a href="#def-string">string</a> (generally a number)</span>,
  "citations": [
      {
          "type": <span class="json-data-type">"official" or "parallel"</span>,
          "cite": <span class="json-data-type"><a href="#def-string">string</a></span>
      }
  ],
  "volume": {
      "url": <span class="json-data-type"><a href="#def-url">url</a></span>,
      "volume_number": <span class="json-data-type"><a href="#def-string">string</a> (generally a number)</span>
  },
  "reporter": {
      "url": <span class="json-data-type"><a href="#def-url">url</a></span>,
      "full_name": <span class="json-data-type"><a href="#def-string">string</a></span>
  },
  "court": {
      "url": <span class="json-data-type"><a href="#def-url">url</a></span>,
      "id": <span class="json-data-type">integer</span>,
      "slug": <span class="json-data-type"><a href="#def-slug">slug</a></span>,
      "name": <span class="json-data-type"><a href="#def-string">string</a></span>,
      "name_abbreviation": <span class="json-data-type"><a href="#def-string">string</a></span>
  },
  "jurisdiction": {
      "url": <span class="json-data-type"><a href="#def-url">url</a></span>,
      "id": <span class="json-data-type">integer</span>,
      "slug": <span class="json-data-type"><a href="#def-slug">slug</a></span>,
      "name": <span class="json-data-type"><a href="#def-string">string</a></span>,
      "name_long": <span class="json-data-type"><a href="#def-string">string</a></span>,
      "whitelisted": <span class="json-data-type">"true" or "false"</span>
  },
  <span class="code-example-casebody-section">
  "casebody": {
      "data": {
          "judges": [],
          "head_matter": <span class="json-data-type"><a href="#def-string">string</a></span>
          "attorneys": [
            <span class="json-data-type"><a href="#def-string">string</a></span>
          ],
          "opinions": [
              {
                  "type": <span class="json-data-type"><a href="#def-string">string</a></span>,
                  "author": <span class="json-data-type"><a href="#def-string">string</a></span>,
                  "text": <span class="json-data-type"><a href="#def-string">string</a></span>
              }
          ],
          "parties": [
              <span class="json-data-type"><a href="#def-string">string</a></span>
          ]
      },
      "status": <span class="json-data-type">should be "ok"</span>
  }
  </span>
}</pre>
    {# ==============> reporters <============== #}
    <dt>
      <a id="endpoint-reporters"></a>
      Reporters
    </dt>
    <dd>
      <a class="endpoint-link" href="{% api_url "reporter-list" %}">{% api_url "reporter-list" %}</a>
      <p class="endpoint-description">
        This will return a list of reporter series.
      </p>
      <h5 class="list-header">Endpoint Parameters:</h5>
      <ul class="parameter-list">
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">full_name</code></h5>
          <ul>
            <li class="param-data-type"> e.g. Illinois Appellate Court Reports</li>
            <li class="param-description"> the full reporter name</li>
          </ul>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">short_name</code></h5>
          <ul>
            <li class="param-data-type"> e.g. Ill. App.</li>
            <li class="param-description"> the abbreviated name for the reporter</li>
          </ul>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">start_year</code></h5>
          <ul>
            <li class="param-data-type"> YYYY</li>
            <li class="param-description"> the earliest year reported on in the series</li>
          </ul>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">end_year</code></h5>
          <ul>
            <li class="param-data-type"> YYYY</li>
            <li class="param-description"> the latest year reported on in the series</li>
          </ul>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">volume_count</code></h5>
          <ul>
            <li class="param-data-type"> integer</li>
            <li class="param-description"> filter on the number of volumes in a reporter
              series
            </li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">cursor</code></h5>
          <ul>
            <li class="param-data-type"> An randomly generated <a href="#def-string">string</a></li>
            <li class="param-description">
              This field contains a value that we generate which will bring you to a specific page of results.
            </li>
          </ul>
        </li>
      </ul>
    </dd>

    {# ==============> jurisdictions <============== #}
    <dt>
      <a id="endpoint-jurisdictions"></a>
      Jurisdictions
    </dt>
    <dd>
      <a class="endpoint-link" href="{% api_url "jurisdiction-list" %}">{% api_url "jurisdiction-list" %}</a>
      <p class="endpoint-description">
        This will return a list of jurisdictions.
      </p>
      <h5 class="list-header">Endpoint Parameters:</h5>
      <ul class="parameter-list">
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">id</code></h5>
          <ul>
            <li class="param-data-type"> integer</li>
            <li class="param-description"> get jurisdiction by ID</li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">name</code></h5>
          <ul>
            <li class="param-data-type"> e.g. <code>Ill.</code></li>
            <li class="param-description"> abbreviated jurisdiction name</li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">name_long</code></h5>
          <ul>
            <li class="param-data-type"> e.g. <code>Illinois</code></li>
            <li class="param-description"> full jurisdiction name</li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">whitelisted</code></h5>
          <ul>
            <li class="param-data-type"><code>true</code> or <code>false</code></li>
            <li class="param-description"> filter for <a href="#def-whitelisted">whitelisted</a> cases</li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">slug</code></h5>
          <ul>
            <li class="param-data-type"> a <a href="#def-slug">slug</a></li>
            <li class="param-description"> filter on the jurisdiction <a href="#def-slug">slug</a></li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">cursor</code></h5>
          <ul>
            <li class="param-data-type"> An randomly generated <a href="#def-string">string</a></li>
            <li class="param-description">
              This field contains a value that we generate which will bring you to a specific page of results.
            </li>
          </ul>
        </li>
      </ul>
    </dd>

    {# ==============> courts <============== #}
    <dt>
      <a id="endpoint-courts"></a>
      Courts
    </dt>
    <dd>
      <a class="endpoint-link" href="{% api_url "court-list" %}">{% api_url "court-list" %}</a>
      <p class="endpoint-description">
        This will return a list of courts.
      </p>
      <h5 class="list-header">Endpoint Parameters:</h5>
      <ul class="parameter-list">
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">id</code></h5>
          <ul>
            <li class="param-data-type"> integer</li>
            <li class="param-description"> get courts by ID</li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">slug</code></h5>
          <ul>
            <li class="param-data-type"> a <a href="#def-slug">slug</a></li>
            <li class="param-description"> filter on the court <a href="#def-slug">slug</a></li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">name</code></h5>
          <ul>
            <li class="param-data-type"> e.g. <code>Illinois Appellate Court</code></li>
            <li class="param-description"> full court name</li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">name_abbreviation</code></h5>
          <ul>
            <li class="param-data-type">e.g. <code>Ill. App. Ct.</code></li>
            <li class="param-description"> abbreviated court name</li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">jurisdiction</code></h5>
          <ul>
            <li class="param-data-type"><a href="#def-slug">slug</a></li>
            <li class="param-description"><a href="#endpoint-jurisdictions">jurisdiction</a> <a
                href="#def-slug">slug</a></li>
          </ul>
        </li>
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">cursor</code></h5>
          <ul>
            <li class="param-data-type"> An randomly generated <a href="#def-string">string</a></li>
            <li class="param-description">
              This field contains a value that we generate which will bring you to a specific page of results.
            </li>
          </ul>
        </li>
      </ul>
    </dd>

    {# ==============> volumes <============== #}
    <dt>
      <a id="endpoint-volumes"></a>
      Volumes
    </dt>
    <dd>
      <a class="endpoint-link" href="{% api_url "volumemetadata-list" %}">{% api_url "volumemetadata-list" %}</a>
      <p class="endpoint-description">
        This will return a complete list of volumes.
      </p>
      <h5 class="list-header">Endpoint Parameters:</h5>
      <ul class="parameter-list">
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">cursor</code></h5>
          <ul>
            <li class="param-data-type"> An randomly generated <a href="#def-string">string</a></li>
            <li class="param-description">
              This field contains a value that we generate which will bring you to a specific page of results.
            </li>
          </ul>
        </li>
      </ul>
    </dd>

    <dt>
      <a id="endpoint-volumes"></a>
      Citations
    </dt>
    <dd>
      <a class="endpoint-link" href="{% api_url "citation-list" %}">{% api_url "citation-list" %}</a>
      <p class="endpoint-description">
        This will return a list of citations.
      </p>
      <h5 class="list-header">Endpoint Parameters:</h5>
      <ul class="parameter-list">
        <li class="list-group-item">
          <h5 class="list-header"><code class="parameter-name">cursor</code></h5>
          <ul>
            <li class="param-data-type"> An randomly generated <a href="#def-string">string</a></li>
            <li class="param-description">
              This field contains a value that we generate which will bring you to a specific page of results.
            </li>
          </ul>
        </li>
      </ul>
    </dd>
  </dl>

  {# ==============> BEGINNERS <============== #}
  <h2 class="subtitle" id="beginners">
    Beginner's Introduction to APIs
  </h2>
  <p>
    Are you a little lost in all the technical jargon, but still want to give the API a shot? This is a good place to
    start! This is by no means a complete introduction to using <a href="#def-api">APIs</a>, but it might be just
    enough to help situate a technically inclined person who's a bit outside of their comfort zone. If you've had
    enough and would prefer to just access the cases using a human-centric interface, please check out our
    <a href="{% url 'search' %}">search tool</a>.
  </p>
  <p>
    Fundamentally, an API is no different from a regular website: A program on your computer, such as a web
    browser or <a href="#def-curl">curl</a> sends a bit of data to a <a href="#def-server">server</a>, the
    server processes that data, and then sends a response. If you know how to read a
    <a href="#def-url">URL</a>, you can interact with web-based services in ways that aren't limited to
    clicking on the links and buttons on the screen.
  </p>
  <p>
    Consider the following <a href="#def-url">URL</a>, which will
    <a href="https://www.google.com/search?q=CAP">perform a google search for the word "CAP."</a>
  </p>
  <pre><code>https://www.google.com/search?q=CAP</code></pre>
  <p>
    Let's break it down into its individual parts:
  </p>
  <pre><code>https://</code></pre>
  <p>
    This first part tells your web browser which protocol to use: this isn't very
    important for our purposes, so we'll ignore it.
  </p>
  <pre><code>www.google.com</code></pre>
  <p>
    The next part is a list of words, separated by periods, between the initial double-slash, and before the
    subsequent single slash. Many people generically refer to this as the domain, which is only partly true,
    but the reason why that's not entirely true isn't really important for our purposes; the important
    consideration here is that it points to a specific <a href="#def-server">server</a>, which is just another
    computer on the internet.
  </p>
  <pre><code>/search</code></pre>
  <p>
    The next section, which is comprised of everything between the slash after the server name and the
    question mark, is called the <a href="#def-path">path</a>. It's called a path because, in the earlier days
    of the web, it was a 'path' through folders/directories to find a specific file on the web server. These
    days, it's more likely that the path will point to a specific <a href="#def-endpoint">endpoint</a>.
  </p>
  <p>
    You can think of an endpoint as a distinct part of a program, which could require specific inputs,
    and/or provide different results. For example, the "login" endpoint on a website might accept a
    valid username and a password for input, and return a message that you've successfully logged in. A
    "register" endpoint might accept various bits of identifying information, and return a screen that
    says your account was successfully registered.
  </p>
  <p>
    Though there is only one part of this particular path, <code>search</code>, developers usually
    organize paths into hierarchical lists separated by slashes. Hypothetically, if the developers at
    Google decided that one generalized search endpoint wasn't sufficiently serving people who wanted to
    search for books or locations, they could implement more specific endpoints such as
    <code>/search/books</code> and <code>/search/locations</code>.
  </p>
  <pre><code>?q=CAP</code></pre>
  <p>
    The final section of the URL is where you'll find the <a href="#def-parameter">parameters</a>, and is
    comprised of everything after the question mark. Parameters are a way of passing individual, labelled
    pieces of information to the endpoint to help it perform its job. In this case, the parameter tells the
    <code>/search</code> endpoint what to search for. Without this parameter, the response wouldn't be
    particularly useful.
  </p>
  <p>
    A URL can contain many parameters, separated by ampersands, but in this instance, there is only one
    parameter: the rather cryptically named "q," which is short for "query," which has a value of "CAP."
    Parameter names are arbitrary— Google's developers could just as easily have set the parameter name
    to <code>?query=CAP</code>, but decided that "q" would sufficiently communicate its purpose.
  </p>
  <p>
    The Google developers designed their web search endpoint to accept other parameters, too. For
    example, there is an even more cryptically named parameter, 'tbs' which will limit the age of the
    documents returned in the search results. The parameters <code>?q=CAP&tbs=qdr:y</code> will perform
    a web search for "CAP" and limit the results to documents less than a year old.
  </p>
  <p>
    So when you're working with CAPAPI, the same principles apply. Rather than http://www.google.com, you'll
    be using {% api_url "api-root" %}. Rather than using the /search?q= endpoint and parameter, you'll
    be using one of our <a href="#endpoints">endpoints and the parameters we've defined</a>. One important
    difference is the purpose of the structured data we're returning, vs. the visual, browser-oriented data
    that google is returning with their search engine.
  </p>
  <p>
    When you perform a query in a web browser using our API, there are some links and buttons, but the data
    itself is in a text-based format with lots of brackets and commas. This format is called JSON, or
    JavaScript Object Notation. We use this format because software developers can easily utilize data in that
    format in their own programs. We do intend to have a more user-friendly case browser at some point soon,
    but we're not quite there yet.
  </p>
  <p>
    OK! That about does it for our beginner's introduction to web-based APIs. Please check out our
    <a href="#examples">usage examples</a> section to see some of the ways you can put these principles to
    work in CAPAPI. If you have any suggestions for making this documentation better, we'd appreciate your
    taking the time to let us know in an issue report
    <a href="https://github.com/harvard-lil/capstone/issues">in our code repository on github.com</a>.
  </p>
  <p>
    Thanks, and good luck!
  </p>

  {# ==============> PROBLEMS <============== #}
  <h2 class="subtitle" id="problems">
    Reporting Problems and Enhancement Requests
  </h2>
  <p>
    We are serving an imperfect, living dataset through an API that will forever be a work-in-progress. We
    work hard to hunt down and fix problems in both the API and the data, but a robust user base will uncover
    problems more quickly than our small team could ever hope to. Here's the best way to report common types
    of errors.
  </p>
  <dl>
    <ul>
      <li><a href="https://github.com/harvard-lil/capstone#errata">Our data errata</a></li>
      <li><a href="https://github.com/harvard-lil/capstone/issues">Our issue tracker</a></li>
      <li><a href="https://github.com/harvard-lil/capstone">Our Github repository</a></li>
    </ul>
    <dt>
      Jumbled or Misspelled Words in Case Text
    </dt>
    <dd>
      For now, we're not accepting bug reports for <a href="#def-ocr">OCR</a> problems. While our data is
      good quality for OCR'd text, we fully expect these errors in every case.  We're working on the best way
      to tackle this.
    </dd>
    <dt>
      Typos or Broken Links in Documentation or Website, API Error Messages or Performance Problems, and
      Missing Features
    </dt>
    <dd>
      First, please check our existing <a href="https://github.com/harvard-lil/capstone/issues">issues</a> to
      see if someone has already reported the problem. If so, please feel free to comment on the issue to add
      information. We'll update the issue when there's more information about the issue, so if you'd like
      notifications, click on the "Subscribe" button on the right-hand side of the screen. If no issue exists,
      create a new issue, and we'll get back to you as soon as we can.
    </dd>

    <dt>Incorrect Metadata or Improperly Labelled data in XML</dt>
    <dd>
      First, check our <a href="https://github.com/harvard-lil/capstone#errata">errata</a> to see if this is
      a known issue. Then, check our existing
      <a href="https://github.com/harvard-lil/capstone/issues">issues</a> to see if someone has already
      reported the problem. If so, please feel free to comment on the issue to add context or additional
      instances that the issue owner didn't report. We'll update the issue when there's more information about
      the issue, so if you'd like notifications, click on the "Subscribe" button on the right-hand side of the
      screen. If no issue exists, create a new issue and we'll get back to you as soon as we can.
    </dd>
  </dl>

  {# ==============> GLOSSARY <============== #}
  <h2 class="subtitle" id="glossary">
    Glossary
  </h2>
  <p>
    This is a list of technical or project-specific terms we use in this documentation. These are stub
    definitions to help you get unstuck, but they should not be considered authoritative or complete. A quick
    Google search should provide more context for any of these terms.
  </p>
  <dl>
    <dt>
      <a id="def-api"></a>
      API
    </dt>
    <dd>
      API is an acronym for Application Programming Interface. Broadly, it is a way for one computer program
      to transfer data to another computer program. CAPAPI is a <a href="#def-restful">RESTful</a> API
      designed to distribute court case data.
    </dd>


    <dt>
      <a id="def-character"></a>
      <a id="def-special-character"></a>
      Character
    </dt>
    <dd>
      A letter, number, space, or piece of punctuation. Multiple characters together make up a
      <a href="#def-string">string</a>.
    </dd>
    <dd>
      Special characters are characters that have programmatic significance to a program. The "specialness"
      of any given character is determined by the context in which it's used. For example, you can't add a
      bare question mark to your path because they indicate to the server that everything after them is a
      <a href="#def-parameter">parameter</a>.
    </dd>

    <dt>
      <a id="def-command-line"></a>
      Command Line
    </dt>
    <dd>
      This is the textual interface for interacting with a computer. Rather than interacting with the system
      through windows and mouse clicks, commands are typed and output is rendered in its textual form. On mac,
      the default Command Line program is Terminal. On Windows, the program is cmd.exe.
    </dd>

    <dt>
      <a id="def-curl"></a>
      curl
    </dt>
    <dd>
      <a href="https://curl.haxx.se/">curl</a> is a simple <a href="#def-command-line">command line</a> tool
      for retrieving data over the internet. It's similar to a web browser in that it will retrieve the
      contents of a <a href="#def-url">url</a>, but it will dump the text contents to a terminal, rather than
      show a rendered version in a graphical browser window.
    </dd>

    <dt>
      <a id="def-endpoint"></a>
      Endpoint
    </dt>
    <dd>
      You can think of an endpoint as a distinct part of a program, which could require specific inputs,
      and/or provide different results. For example, the "login" endpoint on a website might accept a valid
      username and a password for input, and return a message that you've successfully logged in. A "register"
      endpoint might accept various bits of identifying information, and return a screen that says your
      account was successfully registered.
    </dd>

    <dt>
      <a id="def-jurisdiction"></a>
      Jurisdiction
    </dt>
    <dd>
      The jurisdiction of a case or volume is the political division it belongs to, such as the United States, a state,
      a territory, a tribe, or the District of Columbia. Volumes that collect cases from a region have the jurisdiction
      "Regional." Cases from tribal courts (other than Navajo Nation) temporarily have the jurisdiction
      "Tribal Jurisdictions" while we verify the correct jurisdiction for each tribal court.
    </dd>

    <dt>
      <a id="def-ocr"></a>
      OCR
    </dt>
    <dd>
      OCR is a process in which a computer attempts to create text from an image of text. The text in our
      cases is OCR-derived using scanned case reporter pages as source images.
    </dd>

    <dt>
      <a id="def-restful"></a>
      RESTful
    </dt>
    <dd>
      A RESTful <a href="#def-api">API</a> is based on
      <a href="https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol">HTTP</a>, and makes use of its
      built-in verbs(commands), such as GET and POST.
    </dd>
    <dt>
      <a id="def-reporter"></a>
      Reporter
    </dt>
    <dd>
      In this project, we use the term 'reporter' to refer to a reporter series. We'd consider F2d. a
      reporter.
    </dd>
    <dt>
      <a id="def-server"></a>
      Server
    </dt>
    <dd>
      A server is just a computer on the internet that was configured to respond to requests from other
      computers. A web server will respond to requests from a web browser. An email server will respond to
      requests from email programs, and or other email servers which are sending it messages.
    </dd>
    <dt>
      <a id="def-slug"></a>
      Slug
    </dt>
    <dd>
      A <a href="#def-string">string</a> with <a href="#def-special-character">special characters</a> removed
      for ease of inclusion in a <a href="#def-url">URL</a>.
    </dd>
    <dt>
      <a id="def-string"></a>
      String
    </dt>
    <dd>
      A string, as a type of data, just means an arbitrary list (or string) of
      <a href="#def-character">characters</a>. A word is a string. This whole sentence is a string. "h3ll0.!"
      is a string. This whole document is a string.
    </dd>

    <dt>
      <a id="def-tld"></a>
      Top-Level Domain
    </dt>
    <dd>
      The suffix to a domain name, such as <code>.com</code>, <code>.edu</code> or <code>.co.uk</code>.
    </dd>

    <dt>
      <a id="def-url"></a>
      URL
    </dt>
    <dd>
      A URL, or Uniform Resource Locator, is an internet address that generally contains a communication
      protocol, a server name, a path to a file or endpoint, and possibly parameters to pass to the endpoint.
    </dd>
    <dt>
      <a id="def-parameter"></a>
      URL Parameter
    </dt>
    <dd>
      For our purposes, a parameter is just a piece of data with a label that can be passed to an
      <a href="#def-endpoint">endpoint</a> in a web request.
    </dd>
    <dt>
      <a id="def-path"></a>
      URL Path
    </dt>
    <dd>
      The URL path begins with the slash after the <a href="#def-tld">top-level domain</a> and ends with the
      question mark that signals the beginning of the <a href="#def-parameter">parameters</a>. It was
      originally intended to point to a file on the server's hard drive, but these days it's just as likely to
      point to an application <a href="#def-endpoint">endpoint</a>.
    </dd>
    <dt>
      <a id="def-whitelisted"></a>
      Whitelisted
    </dt>
    <dd>
      While most cases in the database are subject to a 500 case per day access limit, jurisdictions that
      publish their cases in a citable, machine-readable format are not subject to this limit.
      <a href="#limits">Click here for more information on access limits, what type of users
        aren't subject to them, and how you can eliminate them in your legal jurisdiction.</a>
    </dd>
  </dl>
{% endblock %}
