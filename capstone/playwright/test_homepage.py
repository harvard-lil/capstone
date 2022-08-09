import re
from playwright.sync_api import Page, expect

url = "http://case.test:8000"

def test_state_onclick_loads_correct_page(page: Page, ordered_list_state_abbreviations):
  page.goto(url)
  for _state in ordered_list_state_abbreviations:
    expected_url = '//cite.case.test:8000/#' + _state
    selector = '#' + _state
    loc = page.locator(selector)
    expect(loc).to_have_attribute('href', expected_url)

