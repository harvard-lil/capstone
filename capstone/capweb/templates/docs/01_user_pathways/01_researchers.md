{% load docs_url %}{% load api_url %}
title: Getting Researcher Access
short_title: For Researchers
explainer: Want to get started with data from the Caselaw Access Project but aren't sure where to start? This guide will point you in the right direction for your use case.

This document will guide you through getting access to CAP data. We will:

* Briefly explain our primary data access tools and what each is useful for.
* Show you where to get more information about registering, using the tools and data, and using our site.
* Help you determine what level of access you need to access the data you're interested in for your research.


# How do you want to access caselaw data? 

We offer a number of tools to access caselaw, which you can browse at our
[tools page]({% url "tools" %}).

If you are interested in offline computational analysis, you might be particularly
interested in the API and Bulk Downloads.
Which one is right for you depends on your use case. The data
allowances are exactly the same using both methods.

## Bulk Downloads

Bulk downloads are large, zipped files with conveniently formatted data
for stream processing.
They are useful for tasks like natural language processing where you want
to download large numbers of cases by court or jurisdiction and filter them
locally.

* [Bulk Downloads User Guide]({% docs_url 'bulk' %})
* [Bulk Download Page]({% url 'download-files' 'bulk_exports/' %})

## API

Our RESTful API is useful for users who need to work interactively with
our data without downloading all of it or need more customized/filtered
data rather than one monolithic download.

*   [API Reference]({% docs_url 'api' %})
*   [Interactive API Browser]({% api_url 'api-root' %})
*   [API Learning Track]({% docs_url 'APIs' %})

# What level of access do you need?

Whether you're using the API or bulk downloading, there are some data
access considerations to keep in mind. Some of our data is entirely
unrestricted and doesn't even require a login or API token. Some is
limited to a certain number of cases per day for most users. Academic
researcher accounts are entirely unrestricted, but must sign an
agreement limiting their ability to redistribute the data.

Many types of data are available without logging in and without
restriction.

*   Metadata
*   N-gram statistics
*   Citation graphs
*   Case text from open jurisdictions:
    *   Illinois
    *   Arkansas
    *   North Carolina
    *   New Mexico

If your use case is satisfied by these, you don't even need to
create an account. Just start querying the API or downloading available
bulk data, and you're good to go.

If you need API access to case text from restricted jurisdictions, you'll at
least need to create an account to authenticate your API
requests. If you need 500 or fewer case texts per day,
that's all you need.

If you must access more than 500 case texts per day from restricted
jurisdictions, you will need an unthrottled researcher account.

Headnotes and other publisher-created work added to cases after 1924 are
not available through this project.

# How do I register?

Check out our quick [Registration
Guide]({% docs_url 'registration' %}). If
you need it, you can find your API key by clicking on the ACCOUNT link
at the top of the page.

# How do I apply for researcher access?

If you are a research scholar and your work requires access to the full text of more than 500 cases per day, you may 
apply for unmetered access via your account page.

## Important Caveats
You must enter into a special bulk access agreement with LexisNexis, which prohibits you from:

*  **using the cases for non-research or commercial purposes and**
*  **sharing bulk caselaw with others.**

## Eligibility

To be eligible, you must demonstrate that you are a research scholar.

## Where do I apply?
 
Once you have an account:
 
### Harvard community members {: data-toc-label='Harvard' }

If you are a member of the Harvard community with a Harvard email address, you can 
[sign the Harvard bulk access agreement]({% url "harvard-research-request-intro" %}) and you will immediately have full 
access from Harvard IP addresses.

### Other Educational or non-profit affiliates {: data-toc-label='Other Institutions' }

If you are officially affiliated with an educational or non-profit research institution, 
[sign this application to request access]({% url "affiliated-research-request" %}) and your application will be 
reviewed shortly.

### Other researchers {: data-toc-label='Others' }

If you do not otherwise qualify for unmetered access, [fill out this form]({% url "unaffiliated-research-request" %}) 
to explain your standing as an independent research scholar and we will do our best to work with you or refer you to an 
appropriate organization.

Please [contact us]({% url "contact" %}) with any questions.