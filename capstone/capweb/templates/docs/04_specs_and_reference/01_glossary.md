{% load docs_url %}
title: Documentation Glossary
meta_description: Caselaw Access Project Documentation Glossary
explainer: The Caselaw Access Project API, also known as CAPAPI, serves all official US court cases published in books from 1658 to 2018. The collection includes over six million cases scanned from the Harvard Law School Library shelves. <a href="{% url "about" }>Learn more about the project</a>.

{# ==============> GLOSSARY <============== #}
  
This is a list of technical or project-specific terms we use in this documentation. These are stub definitions to help
you get unstuck, but they should not be considered authoritative or complete. A quick Google search should provide more
context for any of these terms.

# API {: id="def-api" }
API is an acronym for Application Programming Interface. Broadly, it is a way for one computer program to transfer
data to another computer program. CAPAPI is a [RESTful](#def-restful) API designed to distribute court case data.


# Character {: id="def-character" }
A letter, number, space, or piece of punctuation. Multiple characters together make up a [string](#def-string).
  
  
# Special Character {: id="def-special-character" }
Characters that have programmatic significance to a program. The "specialness" of any given
character is determined by the context in which it's used. For example, you can't add a bare question mark to your path
because they indicate to the server that everything after them is a [parameter](#def-parameter).


# Command Line {: id="def-command-line" }
A textual interface for interacting with a computer. Rather than interacting with the system through windows
 and mouse clicks, the user types commands and output is rendered in textual form. On a Mac, the default command-line
 program is Terminal. On Windows, the program is `cmd.exe`.


# curl {: id="def-curl" }
[curl](https://curl.haxx.se/) is a [command-line](#def-command-line) tool for retrieving data over the
internet. It's similar to a web browser in that it will retrieve the contents of a [URL](#def-url), but it will dump the
 text contents to a terminal, rather than show a rendered version in a graphical browser window.
  
  
# Endpoint {: id="def-endpoint" }
A distinct part of a program which could require specific inputs and provide
different results. For example, the `/login` endpoint on a website might accept a valid username and a password for
input and return a message that you've successfully logged in. A `/register` endpoint might accept various bits of
identifying information, and return a screen that says your account was successfully registered.
  

# Jurisdiction {: id="def-jurisdiction" }
The political division a case belongs to, such as the United States, a state, a
territory, a tribe, or the District of Columbia. Volumes that collect cases from a region have the jurisdiction
"Regional." Cases from tribal courts (other than Navajo Nation) temporarily have the jurisdiction "Tribal Jurisdictions"
while we verify the correct jurisdiction for each tribal court.


# OCR {: id="def-ocr" }
A process in which a computer attempts to create text from an image of text. The text in our cases is
OCR-derived using scanned case reporter pages as source images.


# RESTful {: id="def-restful" }
An [API](#def-api) based on [HTTP](https://en.wikipedia.org/wiki/Hypertext_Transfer_Protocol), that makes use
of its built-in verbs (commands), such as GET and POST.


# Reporter {: id="def-reporter" }
A series of case reports, such as "F." or "F.2d".


# Server {: id="def-server" }
A computer on the internet that is configured to respond to requests from other computers. A web
server will respond to requests from a web browser. An email server will respond to requests from email programs or
other email servers which are sending it messages.


# Slug {: id="def-slug" }
A [string](#def-string) with [special characters](#def-special-character) removed for ease of inclusion in a
[url](#def-url).


# String {: id="def-string" }
A list of [characters](#def-character). A word is a
string. This whole sentence is a string. "h3ll0.!" is a string. This whole document is a string.


# Top-Level Domain {: id="def-tld" }
The suffix to a domain name, such as `.com`, `.edu` or `.co.uk`.


# URL {: id="def-url" }
A Uniform Resource Locator is an internet address that generally contains a communication protocol, a server
name, a path to a file or endpoint, and possibly parameters to pass to the endpoint.


# URL Parameter {: id="def-parameter" }
A piece of data with a label that can be passed to an [endpoint](#def-endpoint) in a web request.


# URL Path {: id="def-path" }
The URL path begins with the slash after the [top-level domain](#def-tld) and ends with the question mark that signals
 the beginning of the [parameters](#def-parameter). It was originally intended to point to a file on the server's hard 
 drive, but these days it's just as likely to point to an application [endpoint](#def-endpoint).


# Open Jurisdiction {: id="def-open" }
While most cases in the database are subject to a 500 case per day access limit, jurisdictions that publish their
cases in a citable, machine-readable format are not subject to this limit. 
For more information on access limits, what type of users aren't subject to them, and how you can eliminate them in your
legal jurisdiction, visit our [access limits]({% docs_url "access_limits" %}) section.


# Restricted Jurisdiction {: id="def-restricted" }
Restricted jurisdictions are subject to a 500 case per day access limit.
For more information on access limits, what type of users aren't subject to them, and how you can eliminate them in your
legal jurisdiction, visit our [access limits]({% docs_url "access_limits" %}) section.


# Cursor {: id="def-cursor" }
This property, populated with a random alphanumeric value, is present in all endpoints. It represents a specific page
of results for a query. You can get the value of the cursor for the next and previous pages from the cursor parameter in
the urls in the `next` and `previous` fields.
