from playwright.sync_api import sync_playwright

URL = "https://smartaxom.nesdr.gov.in/analytics/flood/waterlevelinfo"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)

    context = browser.new_context(ignore_https_errors=True)

    page = context.new_page()

    page.goto(URL, wait_until="networkidle", timeout=60000)

    print(page.title())

    with open("page.html", "w", encoding="utf-8") as f:
        f.write(page.content())

    page.screenshot(path="page.png", full_page=True)

    browser.close()

print("Done")
