This directory contains two ZIP files of images present in
U.S. caselaw.

Scope
-----
Because the OCR process identified certain typographical section
breaks (for instance, a row of asterisks) as images, we have divided
the images into two sets by size, in a rough attempt to separate
"real" and spurious images. There are 167,193 files smaller than 1k in
size, and 97,659 equal to or greater than 1k. The smaller images are
generally not of great interest, but because there are some false
positives, and because the ZIP file is not large, we're presenting it
here along with the larger, presumably real, images.

Note that the OCR process interpreted as images some portions of cases
that we might consider text, like tabular data, forms, or equations.

Connecting images to cases
--------------------------
Image files contained in these ZIP files have names like
`19086-caed4e822f5f5daaf34acc621bd33261.png`; the numerals at the
beginning of the filename, before the hyphen (here, `19086`), are the
case ID in the Caselaw Access Project API. That particular file's
metadata can thus be seen at
[https://api.case.law/v1/cases/19086/](https://api.case.law/v1/cases/19086/);
the record, for _Jackson Cushion Spring Co. v. D’Arcy_, 181 F. 340
(1910), includes a `frontend_url`,
[https://cite.case.law/f/181/340/](https://cite.case.law/f/181/340/),
which links to a human-readable rendering of the case, including
images.

Technical notes
---------------
We extracted the images themselves from an HTML representation of our
raw case body data with [this
code](https://github.com/harvard-lil/capstone/blob/develop/capstone/capdb/tasks.py#L326-L346)
and [this
code](https://github.com/harvard-lil/capstone/blob/develop/capstone/capdb/models.py#L1190-L1226). We
then separated the files with

    find case-images -type f -size -1k -exec cp -an {} case-images-small/ \;

and

    find case-images -type f -not -size -1k -exec cp -an {} case-images-large/ \;

