from playwright.sync_api import expect
import pytest

from capdb.models import Jurisdiction


@pytest.mark.django_db(databases=['default', 'capdb'])
def test_map_links(page, urls, map_data):
    # We run in a loop, rather than parameterizing the test so that:
    # - fixtures only need to be loaded once
    # - the jurisdiction list can be populated from the DB (since tests are parameterized during the collection phase, DB access isn't possible there)
    #
    # Run pytest with -s to print each jurisdiction's slug to the terminal, as it is tested.
    jurisdiction_ids = [
        j.slug for j in Jurisdiction.objects.all() if j.slug not in [
            'native-american',
            'navajo-nation',
            'regional',
            'us',
            'tribal',
            'uk'
       ]
   ]

    for jurisdiction_id in jurisdiction_ids:
        print(f'Checking {jurisdiction_id}')
        page.goto(urls['home'])

        # The map has a link for this jurisdiction
        link = page.locator(f'#{jurisdiction_id}')

        # locator.hover() and locator.click() select an X and Y coordinate inside
        # the element's bounding box. That doesn't work well for complex shapes like these,
        # which include islands and lots of concave edges: hover() and click() may miss,
        # or may catch a neighboring jurisdiction. For example, inspect a#vi.state-link
        # and observe how big the box is... and how small the actual clickable target, the land, is.
        # https://playwright.dev/docs/api/class-locator#locator-click-option-position
        #
        # In lieu of finding coordinates that work for each jurisdiction, and hovering and clicking,
        # we send keyboard focus there, observe that the content updates, and then press enter.
        link.focus()

        # When you hover or focus on the link, the left sidebar content updates
        state_name = link.get_attribute('aria-label')
        left_side_menu = page.locator('.jur_name')
        expect(left_side_menu).to_have_text(state_name)
        link.press('Enter');

        # The link successfully takes you to the expected subsection of the "browse" page
        assert page.url == f'{urls["cite_home"]}#{jurisdiction_id}'
        expect(page.locator(f'h2#{jurisdiction_id}')).to_be_visible()
