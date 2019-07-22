import tempfile
from functools import lru_cache
from io import BytesIO
from pathlib import Path
import img2pdf
from PIL import ImageFont
from PyPDF2 import PdfFileWriter, PdfFileReader
from celery import shared_task
from django.conf import settings
from reportlab import rl_config
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from tqdm import tqdm

from django.db.models import Prefetch

from capdb.models import VolumeMetadata, Citation, PageXML
from capdb.storages import pdf_storage

from scripts.compress_volumes import open_captar_volume, files_by_type
from scripts.helpers import volume_barcode_from_folder, fix_image_file_name
from scripts.refactor_xml import parse


# multiplier to convert pixel dimensions to point dimensions used by PDF, assuming 300 PPI
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

def render_page(barcode, volume_storage, parsed_alto, show_words):
    # read page info from database
    tif_file = Path('images', parsed_alto('alto|fileName').text()).with_suffix('.tif')
    if not volume_storage.exists(tif_file):
        tif_file = tif_file.with_name(fix_image_file_name(barcode, tif_file.name))
        if not volume_storage.exists(tif_file):
            raise ValueError("TIF file %s not found" % tif_file)

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
            font_name, metrics_font = font_lookup.get((font_family, font_types)) or font_lookup.get(
                (font_family, None)) or font_lookup.get(("Times New Roman", None))
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
                int(s.get('HPOS')) * pixels_to_points,  # offset from left side of page, in pts
                height + baseline_offset - (int(s.get('VPOS')) + int(s.get('HEIGHT'))) * pixels_to_points,
                # offset from bottom of page, in pts
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

    return image_pdf_page

@shared_task(acks_late=True)
def make_pdf(volume_path, show_words=False, missing_pages=0):
    """
        Given a volume folder like "redacted/32044057891608_redacted", read image and alto files from
        captar_storage/redacted/<volume> and write a pdf to pdf_storage/32044057891608.pdf.
        Depends on metadata from database.

        show_words: for testing, make selectable text visible
        missing_pages: if using test data, number of pages that are missing from beginning of volume
    """

    print("Loading %s" % volume_path)
    volume_path = Path(volume_path)
    barcode = volume_barcode_from_folder(str(volume_path))

    # read list of files from captar
    with open_captar_volume(volume_path) as volume_storage:

        paths = files_by_type(sorted(volume_storage.iter_files_recursive()))

        # read volume metadata
        if VolumeMetadata.objects.filter(pk=barcode).exists():
            volume_metadata = VolumeMetadata.objects.select_related('reporter').get(pk=barcode)
            volume_number = volume_metadata.volume_number
            reporter_name = volume_metadata.reporter.full_name
            pages = (page.get_parsed_xml() for page in PageXML.objects.filter(volume__metadata=volume_metadata).defer('orig_xml'))
            # read case metadata to add bookmarks to PDF
            bookmarks = []
            for i, case in enumerate(volume_metadata.case_metadatas.prefetch_related(Prefetch('citations', queryset=Citation.objects.filter(type='official'))).all()):
                page = int(case.first_page)
                if case.duplicative:
                    cite = "Case %s" % (i+1)
                else:
                    cite = case.citations.all()[0].cite
                bookmarks.append((page, cite))
        else:
            parsed = parse(volume_storage, paths['volume'][0])
            volume_el = parsed('volume')
            reporter_el = volume_el('reporter')
            volume_number = reporter_el.attr.volnumber
            reporter_name = reporter_el.text()
            pages = (parse(volume_storage, path, remove_namespaces=False) for path in paths['alto'])
            bookmarks = []
            for i, case_path in enumerate(paths['case']):
                parsed_case = parse(volume_storage, case_path, remove_namespaces=False)
                page = int(parsed_case('mets|div[TYPE="volume"] > mets|div').attr("ORDER")) - 1
                if parsed_case('duplicative|casebody'):
                    cite = "Case %s" % (i + 1)
                else:
                    cite = ", ".join(c.text for c in parsed_case('case|citation'))
                bookmarks.append((page, cite))

        with tempfile.TemporaryDirectory() as tempdir:


        # set up PDF
        pdf = PdfFileWriter()
        pdf.addMetadata({'/Title': "%s volume %s" % (reporter_name, volume_number)})
        pdf.addMetadata({'/Creator': 'Harvard Library Innovation Lab'})

        # process each page
        stopit = 0
        for parsed_alto in tqdm(pages):
            stopit += 1
            if stopit == 50:
                break
            pdf.addPage(render_page(barcode, volume_storage, parsed_alto, show_words))

        ### add bookmarks

        bookmarks.sort()
        for page_number, bookmark in bookmarks:
            try:
                pdf.addBookmark(bookmark, page_number - missing_pages)
            except IndexError:
                print("IndexError adding bookmark %s to page %s" % (bookmark, page_number))

    # save pdf to storage
    pdf_path = volume_path.with_name("%s.pdf" % barcode)
    with pdf_storage.open(str(pdf_path), 'wb') as pdf_file:
        pdf.write(pdf_file)