from playwright.sync_api import expect
import pytest


DEFAULT_SEARCH_HASH = '#/?page=1&ordering=relevance'


@pytest.mark.django_db(databases=['default', 'capdb'])
def test_search_button_responds_to_click(page, urls):
    page.goto(urls['search'])
    page.locator("button", has_text="Search").click()
    assert page.url == f"{urls['search']}{DEFAULT_SEARCH_HASH}"


@pytest.mark.django_db(databases=['default', 'capdb'])
def test_search_form_submits_on_enter(page, urls):
    page.goto(urls['search'])
    page.fill('#search','')
    page.keyboard.press('Enter')
    assert page.url == f"{urls['search']}{DEFAULT_SEARCH_HASH}"


@pytest.mark.django_db(databases=['default', 'capdb'])
def test_search_no_results(page, urls, case_factory, elasticsearch):
    term = 'a term with no matches'
    case_factory(name_abbreviation="111 foo bar baz")
    case_factory(name_abbreviation="111 one two three")

    page.goto(urls['search'])
    page.fill('#search', term)
    page.keyboard.press('Enter')
    results_locator = page.locator('.results-list-container')
    expect(results_locator).to_contain_text(f'Full-text search: {term}')
    expect(results_locator).to_contain_text('No Results')


@pytest.mark.django_db(databases=['default', 'capdb'])
def test_search_results_show_correct_count(page, urls, case_factory, elasticsearch):
    term = '111'
    case_factory(name_abbreviation=f"{term} foo bar baz")
    case_factory(name_abbreviation=f"{term} one two three")
    case_factory(name_abbreviation="doesn't match")

    page.goto(urls['search'])
    page.fill('#search', term)
    page.keyboard.press('Enter')
    results_locator = page.locator('.results-list-container')
    expect(results_locator).to_contain_text(f'Full-text search: {term}')
    expect(results_locator).to_contain_text('Results 1 to 2 of 2')


"""
def test_search_page_pagination_next_button_works():
  pass

def test_search_page_pagination_prev_button_works():
  pass

def test_search_tag_is_shown_at_top():
  pass

def test_search_download_button_shows_json_and_csv_buttons():
  pass
"""
