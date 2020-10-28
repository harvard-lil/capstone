{% load static %}
{% load pipeline %}
{% load api_url %}
title: Getting Researcher Access
page_image: img/og_image/docs.png
meta_description: Caselaw Access Project Getting Started Guide.
explainer: Want to get started with data from the Caselaw Access Project but aren't sure where to start? This guide will point you in the right direction for your use case.

This document will guide you through getting access to CAP data. We will:

* Briefly explain our two primary data access tools, what each is useful for.
* Show you where to get more information about registering, using the tools and data, and using our site.
* Help you determine what level of access you need to access the data you're interested in for your research. It will 
explain the pros and cons of unmetered research access and how to apply for it.


# How do you need to access it? 

We offer two primary ways to access our data, API and Bulk Downloads.
Which one is right for you depends entirely on your use case. The data
allowances are exactly the same using both methods.

## Bulk Downloads

Bulk Downloads are large, zipped files with conveniently formatted data.
They are very useful for tasks like NLP, for which having a large amount
of local data without significant customizations is useful.

* [Bulk Downloads User Guide]({% url 'docs' 'user_guides/bulk' %})
* [Bulk Download Page]({% url 'download-files' 'bulk_exports/' %})

## API

Our RESTful API is useful for users who need to work interactively with
our data without downloading all of it or need more customized/filtered
data rather than one monolithic download.

*   [User Guide]({% url 'docs' 'user_guides/api' %})
*   [Reference]({% url 'docs' 'specs_and_reference/api_reference' %})
*   [CAP API Tutorial]({% url 'docs' 'tutorials/api_tutorial' %})
*   [API Root]({% api_url 'api-root' %})
*   [Beginner's introduction to APIs]({% url 'docs' 'tutorials/api_tutorial' %})

# What level of access does your use case require?

Whether you're using the API or Bulk Downloading, there are some data
access considerations to keep in mind. Some of our data is entirely
unrestricted and doesn't even require a login or API token. Some is
limited to a certain number of cases per day for most users. Academic
researcher accounts are entirely unrestricted, but must sign an
agreement limiting their ability to redistribute the data.

Many types of data are available without logging in and entirely without
restriction.

*   All metadata
{: add_list_class="bulleted ml-4" }
*   n-grams
*   Citations
*   Cases from whitelisted jurisdictions:
    *   Illinois
    {: class="ml-4 doc-toc-item" }
    *   Arkansas
    {: class="ml-4 doc-toc-item" }
    *   North Carolina
    {: class="ml-4 doc-toc-item" }
    *   New Mexico
    {: class="ml-4 doc-toc-item" }

If your use case is satisfied by these data, you don't even need to
create an account. Just start querying the API or downloading available
bulk data, and you're good to go.

If you need case text from non-whitelisted jurisdictions, you'll at
least need to create an account to authenticate your API
requests/download access. If you need 500 or fewer case texts per day,
this should be all you need.

If you must access more than 500 case texts per day from non-whitelisted
jurisdictions, you will need an unthrottled researcher account.

Headnotes and other publisher-created work added to cases after 1923 are
not available through this project.

# How do I register?

Check out our quick [Registration
Guide]({% url 'docs' 'user_guides/registration' %}). If
you need it, you can find your API key by clicking on the ACCOUNT link
at the top of the page.

# How do I apply for researcher access?

If you are a research scholar and your work requires access to the full text of more than 500 cases per day, you may 
apply for unmetered access to the full text of all cases made available by the Caselaw Access Project.

## Important Caveats
You must enter into a special bulk access agreement with LexisNexis, which prohibits you from:

*  **using the cases for non-research or commercial purposes and**
*  **sharing bulk caselaw with others.**
{: add_list_class="ordered pl-5" }

## Eligibility {: class="mt-4" }

To be eligible, you must demonstrate that you are a research scholar.

## Where do I apply?
 
### Harvard community members {: class="mt-4" data-toc-label='Harvard' }

If you are a member of the Harvard community with a Harvard email address, you can 
[sign the Harvard bulk access agreement]({% url "harvard-research-request-intro" %}) and you will immediately have full 
access from Harvard IP addresses.

### Other Educational or non-profit affiliates {: class="mt-4" data-toc-label='Other Ed & NP' }

If you are officially affiliated with an educational or non-profit research institution, 
[sign this application to request access]({% url "affiliated-research-request" %}) and your application will be 
reviewed shortly.

### Other researchers {: class="mt-4" data-toc-label='Others' }

If you do not otherwise qualify for unmetered access, [fill out this form]({% url "unaffiliated-research-request" %}) 
to explain your standing as an independent research scholar and we will do our best to work with you or refer you to an 
appropriate organization.


Please [contact us]({% url "contact" %}) with any questions.