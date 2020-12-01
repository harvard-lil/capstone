{% load docs_url %}{% load api_url %}
title: Data Specifications

# Bulk
[Bulk User Guide]({% docs_url 'bulk' %})

## Structure
Bulk data files are provided as zipped directories. Each directory is in
[BagIt format](https://en.wikipedia.org/wiki/BagIt), with a layout like this:

    .
    ├── bag-info.txt
    ├── bagit.txt
    ├── data/
    │   └── data.jsonl.xz
    └── manifest-sha512.txt
    
## Data Format    
Caselaw data is stored within the `data/data.jsonl.xz` file. The `.jsonl.xz` suffix
indicates that the file is compressed with xzip, and is a text file where each line represents a JSON object.
Each line of the JSON file is an object retried from the API.


# API

API queries always return JSON. Here's what they look like. For more details on queries, check out the
[API Reference]({% docs_url 'api' %}).

## Individual Records

If you specify an individual record (reachable through the "url" value present in most types of records) then you'll
receive a single JSON object as formatted below.

## Query Results

If you're not specifying a specific record to return by its primary key (ususally an id,) then your results will be
structured to return multiple objects, even if there's only one hit in your query.

    {
        "count": (int),
        "next": (url with pagination cursor),
        "previous": (url with pagination cursor),
        "results": (array of json objects, as listed below)
    }

# Individual Objects

## Case 

    {
        "id": (int),
        "url": (API url to this case),
        "name": (string),
        "name_abbreviation": (string),
        "decision_date": (string),
        "docket_number": (string),
        "first_page": (string),
        "last_page": (string),
        "citations": [array of citation objects],
        "volume": {Volume Object},
        "reporter": {Reporter Object},
        "court": {Court Object},
        "jurisdiction": {Jurisdiction Object},
        "cites_to": [array of cases this case cites to],
        "frontend_url": (url of case on our website),
        "frontend_pdf_url": (url of case pdf),
        "preview": [array of snippets that contain search term],
        "analysis": {
            "cardinality": (int),
            "char_count": (int),
            "ocr_confidence": (float),
            "sha256": (str),
            "simhash": (str),
            "word_count": (int)
        },
        "last_updated": (datetime),
        "casebody": {
            "status": ok/(error)"
            "data": (null if status is not ok) {
                "judges": [array of strings that contain judges names],
                "parties": [array of strings containing party names],
                "opinions": [
                    {
                        "text": (case text),
                        "type": (string),
                        "author": (string)
                    }
                ],
                "attorneys": [array of strings that contain attorneys names],
                "corrections": (string. May include formatting notes.),
                "head_matter": (elements before the case text)
            }
        }
    }


### Casebody
Without the `full_case=true` parameter set, this query would not have a case body. This can be useful when you want to
browse the metadata of a bunch of cases but only get case data for specific ones, conserving your 500 case text per day 
limit.

This shows the default output for `casebody`— a JSON field with structured plain text. You can change that to HTML or 
XML by setting the `body_format` query parameter to either `html` or `xml`.
  
This is what you can expect from different format specifications using the `body_format` parameter:

Text Format (default)
{: class="topic-header" }

[{% api_url "cases-list" %}?jurisdiction=ill&full_case=true]({% api_url "cases-list" %}?jurisdiction=ill&full_case=true)

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

The XML format is best if your analysis requires more information about pagination, formatting, or page layout. It 
contains a superset of the information available from body_format=text, but requires parsing XML data. Example 
response data:
      
    "data": "<?xml version='1.0' encoding='utf-8'?>\n<casebody ..."

HTML Format
{: class="topic-header" }

[{% api_url "cases-list" %}?jurisdiction=ill&full_case=true&body_format=html]({% api_url "cases-list" %}?jurisdiction=ill&full_case=true&body_format=html)

The HTML format is best if you want to show readable, formatted caselaw to humans. It represents a best-effort attempt 
to transform our XML-formatted data to semantic HTML ready for CSS formatting of your choice. Example response data:

    "data": "<section class=\"casebody\" data-firstpage=\"538\" data-lastpage=\"543\"> ..."
    
    
### Analysis Fields

Each case result in the API returns an analysis section, such as:

    "analysis": { 
        "word_count": 1110, 
        "sha256": "0876189e8ac20dd03b7...", 
        "ocr_confidence": 0.654, 
        "char_count": 6890, 
        "pagerank": { 
            "percentile": 0.31980916105919643, 
            "raw": 5.770123949632993e-08 
         }, 
        "cardinality": 390,
        "simhash": "1:3459aad720da314e" 
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

    
## Jurisdiction 

        {
            "url": (url),
            "id": (int),
            "slug": (string),
            "name": (string),
            "name_long": (string),
            "whitelisted": true/false
        }
        
## Court 

        {
            "id": (int),
            "url": (url),
            "name": (string),
            "name_abbreviation":(string),
            "jurisdiction":(string),
            "jurisdiction_url": (url),
            "slug": (string)
        },
        
        
## Volume 

        {
            "url": (url),
            "barcode": (string),
            "volume_number": (string),
            "title": (string),
            "publisher": (string),
            "publication_year": (int),
            "start_year": (int),
            "end_year": (int),
            "nominative_volume_number": (string),
            "nominative_name": (string),
            "series_volume_number": (string),
            "reporter": (string),
            "reporter_url": (url),
            "jurisdictions": [list of jurisdiction objects],
            "pdf_url": (url),
            "frontend_url": (url)
        },
        
## Reporter 
 
         {
            "id": (int),
            "url": (url),
            "full_name": (string),
            "short_name": (string),
            "start_year": (int),
            "end_year": (int),
            "jurisdictions": [list of jurisdiction objects],
            "frontend_url": (url)
        },
        
## Citation

        {
            "id": (int),
            "cite": (string),
            "cited_by": (url)
        },    
        
        
## Ngrams

        (search term): {
            (string jurisdiction)/"total": [
                {
                    "year": (string),
                    "count": [
                        (int),
                        (int)
                    ],
                    "doc_count": [
                        (int),
                        (int)
                    ]
                }
            ]
        }
