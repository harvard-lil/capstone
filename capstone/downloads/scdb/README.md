This spreadsheet connects CAP's Supreme Court cases with metadata from [SCDB](http://scdb.wustl.edu/), the
  Supreme Court Database.
  
Column definitions:

* `match quality`: the strength of our match, one of "confirmed" (human-verified correct), "strong" (same citation and
  similar case name), "weak" (similar citation and name but likely erroneous), or "none" (no possible match identified)
* `volume number`: U.S. Reports volume number
* `SCDB name`: name of the case in SCDB
* `SCDB cite`: U.S. citation in SCDB
* `SCDB date`: case publication date in SCDB
* `SCDB ID`: case identifier in SCDB
* `CAP name`: name of the case in CAP
* `CAP cite`: U.S. citation in CAP
* `CAP date`: case publication date in CAP
* `CAP ID`: case identifier in CAP, usable in https://api.case.law/v1/cases/<CAP ID>
* `CAP vol id`: volume identifier in CAP, usable in https://api.case.law/v1/volumes/<CAP vol id>
