Derivative datasets, bulk exports, and summaries from the Caselaw Access Project.

Resources you can find here:
----------------------------

* [bulk_exports](./bulk_exports/): zip files of case text and metadata by jurisdiction or reporter.
* [citation graph](./citation_graph): A zipped CSV file of case ids and the case ids they cite to 
* [illustrations](./illustrations/): zip files of the hundreds of thousands of illustrations included by judges in the
  caselaw.
* [PDFs](./PDFs/): PDFs of each volume scanned for CAP, with selectable text created by OCR.
* [scdb](./scdb/): spreadsheets connecting our Supreme Court cases with metadata from [SCDB](http://scdb.wustl.edu/), the
  Supreme Court Database.

Accessing restricted files
--------------------------

Files with "restricted" in the file path, such as bulk exports of raw case text, are only available to download
with a researcher account.

If you have a researcher account you can download restricted files via your browser, or using your API key
with a command like

`wget --header="Authorization: Token abcd12345" "https:{% url "download-files" "restricted/file.zip" %}"`
{: class="code-block" }

(We recommend `wget` over `curl` as it will automatically resume interrupted downloads of large files.)