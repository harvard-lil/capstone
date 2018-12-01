from collections import defaultdict
from functools import lru_cache
from io import BytesIO
from pathlib import Path

import img2pdf
from PIL import ImageFont
from PyPDF2 import PdfFileWriter, PdfFileReader
from django.conf import settings
from reportlab import rl_config
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from django.db.models import Prefetch
from django.utils.text import slugify

from capdb.models import VolumeMetadata, Citation, PageXML
from capdb.storages import CaptarStorage, captar_storage, pdf_storage

# multiplier to convert pixel dimensions to point dimensions used by PDF, assuming 300 PPI
from scripts.helpers import volume_barcode_from_folder

pixels_to_points = 1 / 300 * inch

# lookup table used to turn fonts in alto, like <TextStyle FONTFAMILY="Times New Roman" FONTTYPE="bold italic">,
# into PDF fonts, like "Times-BoldItalic"
font_lookup = {
    ("Times New Roman", None): ("Times-Roman", "Tinos-Regular.ttf"),
    ("Times New Roman", frozenset({'bold'})): ("Times-Bold", "Tinos-Bold.ttf"),
    ("Times New Roman", frozenset({'italic'})): ("Times-Italic", "Tinos-Italic.ttf"),
    ("Times New Roman", frozenset({'bold', 'italic'})): ("Times-BoldItalic", "Tinos-BoldItalic.ttf"),
}
known_font_types = {'bold', 'italic'}
rl_config.useA85 = 0
img2pdf.default_dpi = 300

@lru_cache(maxsize=None)
def get_pil_font(ttf_name, font_size):
    """
        Load a font from services/fonts/ into PIL, identified by a string like "Tinos-Regular.ttf"
    """
    return ImageFont.truetype(str(Path(settings.SERVICES_DIR, "fonts", ttf_name)), int(font_size))

def get_baseline_offset(text, ttf_name, font_size):
    """
        Given a string of text, a font name, and font size, return how far in pts the text extends below the baseline.
    """
    font = get_pil_font(ttf_name, font_size)
    return font.getsize(text)[1] - font.font.ascent

def make_pdf(volume_folder, show_words=False, missing_pages=0):
    """
        Given a volume folder like "32044057891608_redacted", read image and alto files from
        captar_storage/redacted/<volume> and write a pdf to pdf_storage/<volume cite>.pdf.
        Depends on metadata from database.

        show_words: for testing, make selectable text visible
        missing_pages: if using test data, number of pages that are missing from beginning of volume
    """

    # read volume metadata
    volume_metadata = VolumeMetadata.objects.select_related('reporter').get(pk=volume_barcode_from_folder(volume_folder))

    # read case metadata to add bookmarks to PDF
    bookmarks = defaultdict(list)
    for i, case in enumerate(volume_metadata.case_metadatas.prefetch_related(Prefetch('citations', queryset=Citation.objects.filter(type='official'))).all()):
        page = int(case.first_page)
        if case.duplicative:
            bookmarks[page].append("Case %s" % (i+1))
        else:
            cite = case.citations.all()[0]
            bookmarks[page].append(cite.cite)

    # read list of files from captar
    volume_storage = CaptarStorage(captar_storage, Path("redacted", volume_folder))

    # set up PDF
    pdf = PdfFileWriter()
    pdf.addMetadata({'/Title': "%s volume %s" % (volume_metadata.reporter.full_name, volume_metadata.volume_number)})
    pdf.addMetadata({'/Creator': 'Harvard Library Innovation Lab'})

    # process each page
    for page in PageXML.objects.filter(volume__metadata=volume_metadata).defer('orig_xml'):

        # read page info from database
        parsed_alto = page.get_parsed_xml()
        tif_file = Path('images', parsed_alto('alto|fileName').text()).with_suffix('.tif')
        page_number = int(parsed_alto('alto|Page').attr('PHYSICAL_IMG_NR'))

        ### create image page

        # image_pdf_page is created using the img2pdf library, which knows how to import images without recompressing
        with volume_storage.open(tif_file) as image_fp:
            image_pdf_data = img2pdf.convert(image_fp.read())
            image_pdf_page = PdfFileReader(BytesIO(image_pdf_data)).getPage(0)
            media_box = image_pdf_page.mediaBox
            width = float(media_box.getWidth())
            height = float(media_box.getHeight())


        ### create text page

        alto_strings = parsed_alto('alto|String')
        if alto_strings:

            # text_pdf_page is created using reportlab library, which is good at placing words on a page
            text_pdf_buffer = BytesIO()
            text_pdf = canvas.Canvas(text_pdf_buffer, pagesize=(width, height))

            # get styles
            styles = {}
            for style in parsed_alto('alto|TextStyle'):
                # style looks like <TextStyle FONTFAMILY="Times New Roman" FONTSIZE="6.00" FONTTYPE="bold italic" FONTWIDTH="proportional" ID="Style_1"/>
                font_types = frozenset(i for i in style.get('FONTTYPE').split(' ') if i in known_font_types)
                font_family = style.get('FONTFAMILY')
                font_name, metrics_font = font_lookup.get((font_family, font_types)) or font_lookup.get((font_family, None)) or font_lookup.get(("Times New Roman", None))
                styles[style.get('ID')] = {
                    'font_name': font_name,
                    'metrics_font': metrics_font,
                    'size': float(style.get('FONTSIZE')),
                }

            # collect position, contents, and style for each word on the page
            words = []
            for s in alto_strings:
                # s looks like <String CONTENT="DECISIONS" HEIGHT="42" HPOS="415" ID="ST_17.1.1.1" STYLEREFS="Style_8" VPOS="390" WIDTH="501" WC="0.30" CC="000000000" TAGREFS=""/>
                style = styles[s.get('STYLEREFS')]
                text = s.get('CONTENT')
                baseline_offset = get_baseline_offset(text, style['metrics_font'], style['size'])
                words.append([
                    int(s.get('HPOS')) * pixels_to_points,                                      # offset from left side of page, in pts
                    height + baseline_offset - (int(s.get('VPOS')) + int(s.get('HEIGHT'))) * pixels_to_points,    # offset from bottom of page, in pts
                    s.get('CONTENT'),
                    style,
                ])

            # sort words vertically and then horizontally so text selection works
            words.sort(key=lambda word: (-word[1], word[0]))

            # draw words to PDF, changing styles as necessary
            old_style = None
            for x, y, text, style in words:
                if not old_style or style['font_name'] != old_style['font_name'] or style['size'] != old_style['size']:
                    text_pdf.setFont(style['font_name'], style['size'])
                    old_style = style
                text_pdf.drawString(x, y, text, mode=None if show_words else 3)

            text_pdf.save()

            ### combine image page and text page
            text_pdf_page = PdfFileReader(BytesIO(text_pdf_buffer.getvalue())).getPage(0)
            image_pdf_page.mergePage(text_pdf_page)

        # append to pdf
        pdf.addPage(image_pdf_page)

        ### add bookmarks

        if page_number in bookmarks:
            for bookmark in bookmarks[page_number]:
                pdf.addBookmark(bookmark, page_number - 1 - missing_pages)

    # save pdf to storage
    pdf_name = slugify("%s %s" % (volume_metadata.volume_number, volume_metadata.reporter.short_name)) + ".pdf"
    with pdf_storage.open(pdf_name, 'wb') as pdf_file:
        pdf.write(pdf_file)