from playwright.sync_api import Page, expect
import pytest

home_page = "case.test:8000"
cite_page = "cite.case.test:8000"

JURISDICTION_IDS = [
  'ala',
  'alaska',
  'am-samoa',
  'ariz',
  'ark',
  'cal',
  'colo',
  'conn',
  'dakota-territory',
  'dc',
  'del',
  'fla',
  'ga',
  'guam',
  'haw',
  'idaho',
  'ill',
  'ind',
  'iowa',
  'kan',
  'ky',
  'la',
  'mass',
  'md',
  'me',
  'mich',
  'minn',
  'miss',
  'mo',
  'mont',
  'native-american',
  'navajo-nation',
  'nc',
  'nd',
  'neb',
  'nev',
  'nh',
  'nj',
  'nm',
  'n-mar-i',
  'ny',
  'ohio',
  'okla',
  'or',
  'pa',
  'pr',
  'regional',
  'ri',
  'sc',
  'sd',
  'tenn',
  'tex',
  'us',
  'utah',
  'va',
  'vi',
  'vt',
  'wash',
  'wis',
  'w-va',
  'wyo'
]
MAP_JURISDICTION_IDS= [
    j for j in JURISDICTION_IDS if j not in [
        'native-american',
        'navajo-nation',
        'regional',
        'us'
    ]
]

@pytest.mark.parametrize("jurisdiction_id", MAP_JURISDICTION_IDS)
def test_map_links(page: Page, jurisdiction_id):

    page.goto(f'http://{home_page}')

    # The map has a link for this jurisdiction
    link = page.locator(f'#{jurisdiction_id}')
    expect(link).to_have_attribute('href', f'//{cite_page}/#{jurisdiction_id}')

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
    assert page.url == f'http://{cite_page}/#{jurisdiction_id}'
    expect(page.locator(f"h2#{jurisdiction_id}")).to_be_visible()
