import shutil
from pathlib import Path

import pytest
from django.conf import settings

from capdb.models import VolumeMetadata
from fabfile import export_cap_static_volumes, summarize_cap_static, set_case_static_file_names
from test_data.test_fixtures.helpers import check_path, set_case_text


@pytest.mark.django_db(databases=['capdb'])
def test_export_cap_static(reset_sequences, case_factory, jurisdiction_factory, court_factory, redacted_case_factory, volume_metadata_factory, reporter_factory, tmp_path, pytestconfig, django_assert_num_queries):
    # set up a reporter with two volumes, each with three cases
    jurisdiction = jurisdiction_factory(name_long="United States", name="U.S.", slug='us')
    jurisdiction2 = jurisdiction_factory(name_long="Massachusetts", name="Mass.", slug='mass')
    court = court_factory(name="United States Supreme Court", name_abbreviation="U.S.")
    reporter = reporter_factory(full_name="United States Reports", short_name="U.S.", short_name_slug='us')
    reporter.jurisdictions.set([jurisdiction, jurisdiction2])
    volumes = [volume_metadata_factory(volume_number=volume_number, reporter=reporter, redacted=True, barcode=f"123456789{volume_number}") for volume_number in ("1", "2")]
    for volume in volumes:
        case_factory(volume=volume, first_page="1", reporter=reporter, jurisdiction=jurisdiction, citations__cite="1 U.S. 1", court=court)
        c2 = case_factory(volume=volume, first_page="2", reporter=reporter, jurisdiction=jurisdiction, citations__cite="1 U.S. 2", court=court)
        redacted_case_factory(volume=volume, first_page="2", reporter=reporter, jurisdiction=jurisdiction2, citations__cite="1 Mass. 1", court=court)

        # add cite from c2 to c1
        set_case_text(c2, "Cite to 1 U.S. 1")
        c2.sync_case_body_cache()
    # make sure CaseMetadata.static_file_name is set
    set_case_static_file_names()
    # for some reason case_factory is creating extra volumes, so delete those
    VolumeMetadata.objects.exclude(pk__in=[v.pk for v in volumes]).update(out_of_scope=True)

    # run export to temp dir
    with django_assert_num_queries(select=39, update=8, insert=2, delete=2, rollback=2):
        export_cap_static_volumes(dest_dir=str(tmp_path))
    with django_assert_num_queries(select=8):
        summarize_cap_static(str(tmp_path))

    # compare temp dir to test_data/cap_static
    cap_static_dir = Path(settings.BASE_DIR, 'test_data/cap_static')
    if pytestconfig.getoption('recreate_files'):
        # if --recreate_files was passed, copy temp dir to test_data/cap_static instead of checking
        if cap_static_dir.exists():
            shutil.rmtree(cap_static_dir)
        shutil.copytree(tmp_path, cap_static_dir)
    else:
        cap_static_paths = {p.relative_to(cap_static_dir) for p in cap_static_dir.rglob('*')}
        tmp_paths = {p.relative_to(tmp_path) for p in tmp_path.rglob('*')}
        assert cap_static_paths == tmp_paths, "Missing or extra files in cap_static export."
        for path in tmp_path.rglob('*'):
            if not path.is_file():
                continue
            check_path(pytestconfig, path, cap_static_dir / path.relative_to(tmp_path))
