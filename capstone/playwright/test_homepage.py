from playwright.sync_api import Page, expect

url = "http://127.0.0.1:8000"

def test_state_onclick_loads_correct_page(page: Page, ordered_list_state_abbreviations):
    page.goto(url)
    for _state in ordered_list_state_abbreviations:
        expected_url = '//cite.case.test:8000/#' + _state
        selector = '#' + _state
        loc = page.locator(selector)
        expect(loc).to_have_attribute('href', expected_url)


def test_jurisdiction_name_matches_state_hovered(page: Page, ordered_list_state_abbreviations):
    page.goto(url)
    for _state in ordered_list_state_abbreviations[:1]:
        selector = '#' + _state
        # getting 1st element in array since all the g tags besides the 0th index are nested inside 0th index g tag.
        link = page.locator(selector)
        loc = page.locator('g', has=link).nth(1)
        _state_name = loc.all_text_contents()[0]
        link.hover()
        left_side_menu = page.locator('.jur_name')
        expect(left_side_menu).to_have_text(_state_name) 
    
