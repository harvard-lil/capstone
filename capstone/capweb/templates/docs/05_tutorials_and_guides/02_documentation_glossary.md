{% load static %}
{% load pipeline %}
{% load api_url %}
title: Documentation Glossary
page_image: img/og_image/do
meta_description: Caselaw Access Project API Docs
top_section_style: bg-black
row_style: bg-tan
explainer: The Caselaw Access Project API, also known as CAPAPI, serves all official US court cases published in books from 1658 to 2018. The collection includes over six million cases scanned from the Harvard Law School Library shelves. <a href="{% url "about" }>Learn more about the project</a>.

{# ==============> GLOSSARY <============== #}
# Glossary  {: class="subtitle" }
  
This is a list of technical or project-specific terms we use in this documentation. These are stub definitions to help 
you get unstuck, but they should not be considered authoritative or complete. A quick Google search should provide more 
context for any of these terms.

* API
{: class="list-header mb-0" id="def-api" }
* API is an acronym for Application Programming Interface. Broadly, it is a way for one computer program to transfer 
data to another computer program. CAPAPI is a [RESTful]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-restful) API designed to distribute court case data.
{: class="mt-1" }


* Character
{: class="list-header mb-0" id="def-character" }
* A letter, number, space, or piece of punctuation. Multiple characters together make up a [string]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-string).
{: class="mt-1" }
  
  
* Special Character
{: class="list-header mb-0" id="def-special-character" }
* Special characters are characters that have programmatic significance to a program. The "specialness" of any given 
character is determined by the context in which it's used. For example, you can't add a bare question mark to your path 
because they indicate to the server that everything after them is a [parameter]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-parameter).
{: class="mt-1" }


* Command Line
{: class="list-header mb-0" id="def-command-line" }
* This is the textual interface for interacting with a computer. Rather than interacting with the system through windows
 and mouse clicks, commands are typed and output is rendered in its textual form. On mac, the default Command Line 
 program is Terminal. On Windows, the program is cmd.exe.
{: class="mt-1" }


* curl
{: class="list-header mb-0" id="def-curl" }
* [curl](https://curl.haxx.se/) is a simple [command line]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-command-line) tool for retrieving data over the 
internet. It's similar to a web browser in that it will retrieve the contents of a [url]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-url), but it will dump the
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
* A RESTful [API]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-api) is based on [HTTP](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol), and makes use
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
* A [string]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-string) with [special characters]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-special-character) removed for ease of inclusion in a 
[url]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-url).
{: class="mt-1" }


* String
{: class="list-header mb-0" id="def-string" }
* A string, as a type of data, just means an arbitrary list (or string) of [characters]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-character). A word is a 
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
* For our purposes, a parameter is just a piece of data with a label that can be passed to an [endpoint]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-endpoint) 
in a web request.
{: class="mt-1" }


* URL Path
{: class="list-header mb-0" id="def-path" }
* The URL path begins with the slash after the [top-level domain]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-tld) and ends with the question mark that signals
 the beginning of the [parameters]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-parameter). It was originally intended to point to a file on the server's hard 
 drive, but these days it's just as likely to point to an application [endpoint]({% url 'docs' 'tutorials_and_guides/documentation_glossary' %}#def-endpoint).
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


