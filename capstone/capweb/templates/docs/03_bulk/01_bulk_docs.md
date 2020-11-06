{% load pipeline %}
{% load api_url %}
title: Bulk data documentation
meta_description: Caselaw Access Project bulk data documentation
explainer: Our <a href="{% url "download-files" "bulk_exports/" %}">bulk data files</a> contain the same information that is available via <a href="{% url "api" %}">our API</a>, but are much faster to download if you want to interact with a large number of cases. Each file contains all of the cases from a single jurisdiction or reporter. <br/> <a class="btn btn-primary" href="{% url "download-files" "bulk_exports/" %}">Access data</a>
top_section_style: bg-black
row_style: bg-tan

# Access Limits {: class="subtitle" }

All metadata files, and bulk data files for our open jurisdictions, are 
[available to everyone]({% url "download-files" "bulk_exports/" %}) without a login.

Bulk data files for the remaining jurisdictions are available to research scholars who sign a research agreement. You 
can request a research agreement by [creating an account]({% url "register" %}") and then 
[visiting your account page]({% url "user-details" %}).

See our [About page]({% url "about" %}#usage) for details on our data access restrictions.


# Downloading {: class="subtitle" }

You can [download bulk data]({% url "download-files" "bulk_exports/" %}) manually from our website, or
use the [manifest.json]({% url "download-files" "manifest.json" %}) or [manifest.csv]({% url "download-files" "manifest.csv" %})
files to select URLs to download programmatically.

When downloading bulk files, you may find that the download times out on the largest files.
In that case use `wget`, which retries when it encounters a network problem. Here's an example for the
U.S. file with case body in text format:

<pre class="code-block">wget --header="Authorization: Token your-api-token" "{% url "download-files" "bulk_exports/latest/by_jurisdiction/case_text_restricted/us_text.zip" %}"</pre>

Because this is a restricted file it requires an Authorization header.
Replace `your-api-token` with your API token from the [user details]({% url "user-details" %}) page.

# API Equivalence {: class="subtitle" }

Each file that we offer for download is equivalent to a particular query to our API. For example, the file
"ill_text.zip" contains all cases that would be returned by
[an API query]({% api_url "cases-list" %}?full_case=true&jurisdiction=ill&body_format=text)
with `full_case=true&jurisdiction=ill&body_format=text`. We offer files for each possible
`jurisdiction` value and each possible `reporter` value, combined with `body_format=text`, `body_format=xml`,
and plain metadata-only export.

The JSON objects returned by the API and in bulk files differ only in that bulk JSON objects do not include
`"url"` fields, which can be reconstructed from object IDs.


# Data Format {: class="subtitle" }

Bulk data files are provided as zipped directories. Each directory is in
[BagIt format](https://en.wikipedia.org/wiki/BagIt), with a layout like this:

* `Illinois-20180829-text/`
{: add_list_class="bullets" }
    1. `bag-info.txt`
    2. `bagit.txt`
    3. `manifest-sha512.txt`
* `data/`
    4. `data.jsonl.xz`
    
Because the zip file provides no additional compression, we recommend uncompressing it for convenience and
keeping the uncompressed directory on disk.

Caselaw data is stored within the `data/data.jsonl.xz` file. The `.jsonl.xz` suffix
indicates that the file is compressed with xzip, and is a text file where each line represents a JSON object.


# Using Bulk Data {: class="subtitle" }

The `data.jsonl.xz` file can be unzipped using third-party GUI programs like
[The Unarchiver](https://theunarchiver.com/) (Mac) or
[7-zip](https://www.7-zip.org/) (Windows), or from the command line with a command like
`unxz -k data/data.jsonl.xz`.


However, this increases the disk space needed by about 500%, and in most cases is unnecessary. Instead
we recommend interacting directly with the compressed files.


To read the file from the command line, run:

<pre class="code-block">xzcat data/data.jsonl.xz | less</pre>

If you install [jq](https://stedolan.github.io/jq/download/) you can get nicely formatted output ...

`xzcat data/data.jsonl.xz | jq | less`{: class="code-block" }

... or run more sophisticated queries. For example, to extract the name of each case:

<pre class="code-block">xzcat data/data.jsonl.xz | jq .name | less</pre>

You can also interact directly with the compressed files from code. The following example prints
the name of each case using Python:

<pre class="code-block">
import lzma, json
with lzma.open("data/data.jsonl.xz") as in_file:
    for line in in_file:
        case = json.loads(str(line, 'utf8'))
        print(case['name'])
</pre>

To load the compressed data file into an R data frame, do something like this:

<pre class="code-block">
> install.packages("jsonlite")
> library(jsonlite)
> ark <- stream_in(xzfile("Arkansas-20190416-text/data/data.jsonl.xz"))
</pre>

# Other repositories {: class="subtitle" }

You can also explore our Illinois Public Bulk Data on 
[Harvard Dataverse](https://dataverse.harvard.edu/dataverse/caselawaccess){: target="_blank } and 
[Kaggle](https://www.kaggle.com/harvardlil/caselaw-dataset-illinois){: target="_blank" }.
