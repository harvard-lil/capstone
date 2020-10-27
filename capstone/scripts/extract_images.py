import base64
import json
import sys
from multiprocessing import Pool
import fitz

"""
    This script is intended to be run in a subprocess to extract images from a PDF in parallel.
    Images are returned as a json-encoded list of base64-encoded PNGs, for use in the frontend case editor.
    
    Usage:
    
        python extract_images.py pdf_path start end
         
    start and end are inclusive, 1-indexed page numbers, to match the values of Case.first_page_order
    and Case.last_page_order.
"""

def save_pam_as_png(pam):
    """ Conversion function run by multiprocessing pool. """
    return fitz.Pixmap(pam).getPNGdata()


def extract_images(pdf_path, start, end, parallel=False):
    """ Top level function that calls a subprocess per page. """
    doc = fitz.open(pdf_path)
    if end > len(doc):
        raise ValueError("There aren't that many pages in that PDF")
    map_func = Pool().map if parallel else map
    return list(map_func(save_pam_as_png, (
        fitz.Pixmap(doc, doc.getPageImageList(n)[0][0]).getImageData('pam')
        for n in range(start-1, end)
    )))


if __name__ == "__main__":
    pdf_path = sys.argv[1]
    start = int(sys.argv[2])
    end = int(sys.argv[3])
    pngs = extract_images(pdf_path, start, end, parallel=True)
    pngs_json = json.dumps([base64.b64encode(png).decode() for png in pngs])
    print(pngs_json)
