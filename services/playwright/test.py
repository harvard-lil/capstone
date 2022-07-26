
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.webkit.launch()
    page = browser.new_page()
    page.goto("http://playwright:8000/")
    page.screenshot(path="example.png")
    browser.close()
