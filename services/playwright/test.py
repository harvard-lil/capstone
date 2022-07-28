import re
from playwright.sync_api import Page, expect

host = "http://web:8000"

def test_homepage_has_Playwright_in_title_and_get_started_link_linking_to_the_intro_page(
    page: Page):
    page.goto(host)

    # Expect a title "to contain" a substring.
    expect(page).to_have_title(re.compile("Playwright"))

    # create a locator
    get_started = page.locator("text=Get Started")

    # Expect an attribute "to be strictly equal" to the value.
    expect(get_started).to_have_attribute("href", "/docs/intro")

    # Click the get started link.
    get_started.click()

    # Expects the URL to contain intro.
    expect(page).to_have_url(re.compile(".*intro"))
