import subprocess
import tempfile
from collections import defaultdict
from functools import lru_cache
from pathlib import Path
import img2pdf
from PIL import ImageFont
from celery import shared_task
from django.conf import settings
from reportlab import rl_config
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from django.db.models import Prefetch

from capdb.models import VolumeMetadata, Citation, PageXML
from capdb.storages import pdf_storage

from scripts.compress_volumes import open_captar_volume, files_by_type
from scripts.helpers import volume_barcode_from_folder, copy_file
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

@lru_cache(maxsize=None)
def get_baseline_offset(text, ttf_name, font_size):
    """
        Given a string of text, a font name, and font size, return how far in pts the text extends below the baseline.
    """
    font = get_pil_font(ttf_name, font_size)
    return font.getsize(text)[1] - font.font.ascent

def get_word_baseline_offset(word, ttf_name, font_size):
    """
        Return maximum get_baseline_offset() for a set of characters.
    """
    chars = set(word)
    return max(get_baseline_offset(c, ttf_name, font_size) for c in chars) if chars else 0

@shared_task(acks_late=True)
def make_pdf(volume_path, show_words=False, replace_existing=False):
    """
        Given a volume folder like "redacted/32044057891608_redacted", read image and alto files from
        captar_storage/redacted/<volume> and write a pdf to pdf_storage/32044057891608.pdf.
        Depends on metadata from database.

        show_words: for testing, make selectable text visible
        replace_existing: if True, replace existing output file instead of canceling job
    """

    volume_path = Path(volume_path)
    barcode = volume_barcode_from_folder(str(volume_path))
    draw_mode = None if show_words else 3
    pdf_path = volume_path.with_name("%s.pdf" % barcode)

    # handle existing output file
    if pdf_path.exists():
        if replace_existing:
            pdf_path.delete()
        else:
            return

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

        # pdf generation pipeline:
        # - write tifs to disk
        # - combine to single multipart tif with tiffcp command line program, recompressing tifs if necessary
        # - convert multipart tif to pdf with tiff2pdf command line program
        # - create text_pdf from ALTO files with reportlab python package
        # - combine tif_pdf and text_pdf with pdftk command line program to get final combined_pdf
        with tempfile.TemporaryDirectory() as tempdir:
            # set up paths
            tempdir = Path(tempdir)
            tifs_path = tempdir / 'tifs'
            tif_combined_path = tempdir / 'tifs.tif'
            tif_pdf_path = tempdir / 'tifs.pdf'
            text_pdf_path = tempdir / 'text.pdf'
            combined_pdf_path = tempdir / 'combined.pdf'

            # write out tifs to disk
            tifs_path.mkdir()
            for tif_path in paths['tif']:
                copy_file(tif_path, tifs_path / Path(tif_path).name, from_storage=volume_storage)

            # combine tifs into multipart tif with tiffcp
            subprocess.check_call([
                                      'tiffcp',
                                      '-r', '-1',  # ensure that tifs have only one strip, so they can be combined by tiff2pdf without re-encoding
                                      '-c', 'g4',  # CCITT Group 4 encoding (same as input)
                                  ] + sorted(str(p) for p in tifs_path.glob('*.tif')) + [  # input files
                                      str(tif_combined_path)  # output file
            ])

            # convert multipart tif to pdf with tiff2pdf
            subprocess.check_call(['tiff2pdf', '-o', str(tif_pdf_path), str(tif_combined_path)])

            # create text_pdf with reportlab, which can't edit existing pdfs but is good at placing words on a page
            text_pdf = canvas.Canvas(str(text_pdf_path))
            text_pdf.setTitle("%s volume %s" % (reporter_name, volume_number))
            text_pdf.setCreator("Harvard Library Innovation Lab")

            # group bookmarks by pagenum
            bookmarks_by_pagenum = defaultdict(list)
            for page_index, label in bookmarks:
                bookmarks_by_pagenum[page_index].append(label)

            # process each page
            for page_index, parsed_alto in enumerate(pages):

                # set page size
                page_el = parsed_alto('alto|Page')
                width = int(page_el.attr('WIDTH')) * pixels_to_points
                height = int(page_el.attr('HEIGHT')) * pixels_to_points
                text_pdf.setPageSize((width, height))

                # add bookmarks
                if page_index in bookmarks_by_pagenum:
                    key = 'p%s' % page_index
                    text_pdf.bookmarkPage(key)
                    for label in bookmarks_by_pagenum[page_index]:
                        text_pdf.addOutlineEntry(label, key)

                # add text
                alto_strings = parsed_alto('alto|String')
                if alto_strings:

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
                        # Words on a pdf page are baseline-positioned, but in alto we have the outside bounding box including descenders.
                        # Calculate distance from bottom of bounding box to baseline:
                        # (This is a very expensive line, so uses multiple levels of caching in the function calls.)
                        baseline_offset = get_word_baseline_offset(text, style['metrics_font'], style['size'])
                        words.append([
                            int(s.get('HPOS')) * pixels_to_points,  # offset from left side of page, in pts
                            height + baseline_offset - (int(s.get('VPOS')) + int(s.get('HEIGHT'))) * pixels_to_points, # offset from bottom of page, in pts
                            s.get('CONTENT'),
                            style,
                        ])

                    # sort words vertically and then horizontally so text selection works
                    words.sort(key=lambda word: (-word[1], word[0]))

                    # draw words to PDF, changing styles as necessary
                    old_style = None
                    for x, y, text, style in words:
                        if not old_style or style['font_name'] != old_style['font_name'] or style['size'] != old_style[
                            'size']:
                            text_pdf.setFont(style['font_name'], style['size'])
                            old_style = style
                        text_pdf.drawString(x, y, text, mode=draw_mode)

                # start next page
                text_pdf.showPage()

            # write out text pdf
            text_pdf.save()

            # combine pdfs
            subprocess.check_call(['pdftk', str(text_pdf_path), 'multibackground', str(tif_pdf_path), 'output', str(combined_pdf_path)])

            # save pdf to storage
            copy_file(combined_pdf_path, pdf_path, to_storage=pdf_storage)
