from playwright.sync_api import Page, expect
url = "http://case.test:8000/search/"


def test_search_no_results_shows_no_results_message(page: Page):
  pass

# use greg
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
