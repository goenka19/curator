"""
Use Playwright to scrape API Hut website for pricing and documentation
"""

from playwright.sync_api import sync_playwright
import json

def check_api_hut():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        try:
            # Go to API Hut
            print("🌐 Loading API Hut...")
            page.goto('https://apihut.in', wait_until='networkidle')
            page.wait_for_timeout(3000)  # Wait for JavaScript to render
            
            # Take screenshot of homepage
            page.screenshot(path='/tmp/apihut_homepage.png')
            print("📸 Screenshot saved: /tmp/apihut_homepage.png")
            
            # Look for Video Downloader API link
            print("\n🔍 Looking for Video Downloader API...")
            
            # Try to find API documentation link
            links = page.query_selector_all('a')
            video_downloader_url = None
            
            for link in links:
                href = link.get_attribute('href') or ''
                text = link.inner_text().lower()
                if 'video' in text or 'downloader' in text or 'instagram' in text:
                    print(f"   Found link: {text[:50]} -> {href}")
                    if 'video' in href or 'downloader' in href:
                        video_downloader_url = href
            
            # If relative URL, make it absolute
            if video_downloader_url and video_downloader_url.startswith('/'):
                video_downloader_url = f"https://apihut.in{video_downloader_url}"
            
            # Go to pricing page
            print("\n💰 Checking Pricing page...")
            page.goto('https://apihut.in/pricing', wait_until='networkidle')
            page.wait_for_timeout(3000)
            
            page.screenshot(path='/tmp/apihut_pricing.png')
            print("📸 Screenshot saved: /tmp/apihut_pricing.png")
            
            # Extract pricing info
            pricing_text = page.inner_text('body')
            print("\n📄 Pricing page content (first 2000 chars):")
            print(pricing_text[:2000])
            
            # Look for video downloader API specifically
            print("\n🔍 Searching for Video Downloader documentation...")
            page.goto('https://apihut.in/api/video-downloader', wait_until='networkidle')
            page.wait_for_timeout(3000)
            
            page.screenshot(path='/tmp/apihut_video_downloader.png')
            print("📸 Screenshot saved: /tmp/apihut_video_downloader.png")
            
            # Get API documentation
            doc_text = page.inner_text('body')
            print("\n📄 Video Downloader API content (first 3000 chars):")
            print(doc_text[:3000])
            
            browser.close()
            print("\n✅ Done! Check the screenshots for visual confirmation.")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            browser.close()

if __name__ == "__main__":
    check_api_hut()
