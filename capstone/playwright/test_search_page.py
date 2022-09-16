from playwright.sync_api import Page, expect
url = "http://case.test:8000/search/"
default_search_url = 'http://case.test:8000/search/#/?page=1&ordering=relevance'
# this search term should produce "No results"
no_results_search_term = 'lil_cap_test'
valid_search_label = 'greg'


def test_search_button_works_aka_updates_url_onclick(page: Page):
  page.goto(url)
  page.locator("button", has_text="Search").click()
  assert page.url == default_search_url

def test_search_pressing_enter_on_fulltextsearch_makes_search(page: Page):
  page.goto(url) 
  page.fill('#search','')
  page.keyboard.press('Enter') 
  assert page.url == default_search_url
  
def test_search_when_no_results_shows_no_results_message(page: Page):
  page.goto(url)
  page.fill('#search',no_results_search_term)
  page.keyboard.press('Enter') 
  results_locator = page.locator('.results-list-container')
  no_results_label = 'No Results'
  expected_result = 'Full-text search: ' + no_results_search_term + '   ' + no_results_label
  expect(results_locator).to_have_text(expected_result)


def test_search_results_show_correct_count(page: Page):
  pass

def test_search_page_pagination_next_button_works(page: Page):
  pass

def test_search_page_pagination_prev_button_works(page: Page):
  pass

def test_search_tag_is_shown_at_top(page: Page):
  pass

def test_search_download_button_shows_json_and_csv_buttons(page: Page):
  pass
