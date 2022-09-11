from playwright.sync_api import Page, expect

url = "http://case.test:8000"
# states that fail, usually the ones where you have to scroll down to click the map
# or states that are too small on the map
# there are errors like "playwright._impl._api_types.Error: Element is outside of the viewport"
# idaho is not at the bottom but playwright clicks "montana" (right above idaho)
# maryland also being too small, playwright clicks "virginia" instead of "montana"
skip = ['dakota-territory', 'am-samoa', 'fla', 'guam', 'haw', 'idaho', 'md', 'mich', 'nj', 'n-mar-i', 'pr', 'vi']

def test_each_state_on_map_contains_valid_url(page: Page, ordered_list_state_abbreviations):
    page.goto(url)
    for _state in ordered_list_state_abbreviations:
        expected_url = '//cite.case.test:8000/#' + _state
        selector = '#' + _state
        loc = page.locator(selector)
        expect(loc).to_have_attribute('href', expected_url)


def test_alabamba_map_link(page, ordered_list_state_abbreviations):
    page.on('response', lambda r: r)
    for _state in ordered_list_state_abbreviations:
      if _state in skip:
        continue
      page.goto("http://case.test:8000")
      #page.evaluate("window.scroll(1,1000);")
      selector = 'a#' + _state
      #if selector[1:] == '#mont' or selector[1:] == '#idaho':
      #  import pdb; pdb.set_trace()
      page.locator(selector).click(force=True)
      assert page.url == "http://cite.case.test:8000/" + selector[1:]


"""
doesn't work because pointer event is intercepted by the svg map, so hovering over a state first triggers the svg point event
def test_jurisdiction_name_matches_state_hovered(page: Page, ordered_list_state_abbreviations):
    page.goto(url)
    for _state in ordered_list_state_abbreviations:
        selector = '#' + _state
        # getting 1st element in array since all the g tags besides the 0th index are nested inside 0th index g tag.
        link = page.locator(selector)
        loc = page.locator('g', has=link).nth(1)
        _state_name = loc.all_text_contents()[0]
        link.hover()
        left_side_menu = page.locator('.jur_name')
        expect(left_side_menu).to_have_text(_state_name) 
"""
