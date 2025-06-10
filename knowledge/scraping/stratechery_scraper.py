#!/usr/bin/env python3
"""
Stratechery scraper using Playwright with cookie persistence.
"""

import os
import json
import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from urllib.parse import urljoin
from pathlib import Path

from playwright.async_api import async_playwright, Page, Browser
from bs4 import BeautifulSoup


class StratecheryScraper:
    """Playwright-based scraper for Stratechery with cookie persistence."""
    
    def __init__(self, output_dir: str = "stratechery_content"):
        self.output_dir = output_dir
        self.base_url = "https://stratechery.com"
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        
        # Cookie storage path
        self.auth_state_path = Path(__file__).parent / "stratechery_auth_state.json"
        
        os.makedirs(output_dir, exist_ok=True)
    
    async def start(self, headless: bool = True):
        """Start the browser with saved authentication state if available."""
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=headless)
        
        # Check if we have saved auth state
        if self.auth_state_path.exists():
            print("Loading saved authentication state...")
            try:
                context = await self.browser.new_context(
                    storage_state=str(self.auth_state_path),
                    viewport={'width': 1920, 'height': 1080},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                self.page = await context.new_page()
                
                # Verify we're still logged in
                await self.page.goto(self.base_url)
                await self.page.wait_for_load_state('networkidle')
                
                if await self._is_logged_in():
                    print("Successfully loaded saved authentication!")
                    return True
                else:
                    print("Saved authentication expired, need to login again...")
                    await context.close()
            except Exception as e:
                print(f"Error loading saved auth state: {e}")
                await context.close()
        
        # Create new context without saved state
        context = await self.browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        )
        self.page = await context.new_page()
        return False
    
    async def login(self) -> bool:
        """Interactive login to Stratechery."""
        print("Navigating to Stratechery...")
        await self.page.goto(self.base_url)
        
        # Check if already logged in
        if await self._is_logged_in():
            print("Already logged in!")
            await self._save_auth_state()
            return True
        
        # Navigate to login page
        print("\nPlease log in to Stratechery in the browser window...")
        print("This may include entering an email verification code.")
        print("Press Enter here AFTER you've fully logged in and can see member content.")
        
        try:
            await self.page.click('a[href*="login"], a[href*="log-in"], a:has-text("Log In")', timeout=5000)
        except:
            await self.page.goto(f"{self.base_url}/log-in")
        
        # Wait for user to indicate they're done
        input("\nPress Enter when you've completed the login process...")
        
        # Verify login worked
        if await self._is_logged_in():
            print("\nLogin successful!")
            await self._save_auth_state()
            return True
        else:
            print("\nLogin not detected. Please try again.")
            return False
    
    async def _save_auth_state(self):
        """Save current authentication state to disk."""
        try:
            await self.page.context.storage_state(path=str(self.auth_state_path))
            print(f"Authentication state saved to {self.auth_state_path}")
        except Exception as e:
            print(f"Error saving auth state: {e}")
    
    async def _is_logged_in(self) -> bool:
        """Check if we're logged in by looking for member-only content."""
        try:
            # Check URL - if we're on a member article, we're logged in
            current_url = self.page.url
            if "/account" in current_url or any(year in current_url for year in ["2024", "2023", "2022"]):
                # Try to find member-only content indicators
                member_content = await self.page.query_selector('.entry-content, .post-content, article')
                if member_content:
                    return True
            
            # Look for account/logout links
            account_link = await self.page.query_selector('a[href*="/account"]')
            logout_link = await self.page.query_selector('a:has-text("Log Out"), a:has-text("Logout")')
            
            return account_link is not None or logout_link is not None
        except:
            return False
    
    async def clear_auth(self):
        """Clear saved authentication state."""
        if self.auth_state_path.exists():
            self.auth_state_path.unlink()
            print("Cleared saved authentication state")
    
    async def explore_structure(self):
        """Interactive exploration mode to understand site structure."""
        print(f"\nCurrently on: {self.page.url}")
        print("Page title:", await self.page.title())
        
        # Get page HTML
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Look for articles
        print("\n=== Article Containers ===")
        for selector in ['article', '.post', '.entry', '.article-content']:
            elements = soup.select(selector)
            if elements:
                print(f"Found {len(elements)} elements matching '{selector}'")
        
        # Look for titles
        print("\n=== Title Elements ===")
        for selector in ['h1.entry-title', 'h2.post-title', '.article-title', 'h1', 'h2']:
            elements = soup.select(selector)[:3]
            for elem in elements:
                text = elem.get_text(strip=True)[:50]
                print(f"{selector}: {text}...")
        
        # Look for content
        print("\n=== Content Areas ===")
        for selector in ['.entry-content', '.post-content', '.article-body', 'main']:
            elements = soup.select(selector)
            if elements:
                print(f"Found content in '{selector}' - {len(elements[0].get_text(strip=True))} chars")
        
        return soup
    
    async def scrape_archive(self, max_pages: Optional[int] = None) -> List[Dict]:
        """Scrape article listings."""
        articles = []
        page_num = 1
        
        while True:
            if max_pages and page_num > max_pages:
                break
            
            url = f"{self.base_url}/archive/page/{page_num}" if page_num > 1 else f"{self.base_url}/archive"
            print(f"\nScraping archive page {page_num}...")
            
            await self.page.goto(url)
            await self.page.wait_for_load_state('networkidle')
            
            # Get all article links
            article_links = await self.page.query_selector_all('article a[href*="/20"], .post a[href*="/20"], h2 a[href*="/20"]')
            
            if not article_links:
                print("No more articles found")
                break
            
            for link in article_links:
                href = await link.get_attribute('href')
                title = await link.text_content()
                
                if href and title:
                    articles.append({
                        'url': urljoin(self.base_url, href),
                        'title': title.strip(),
                        'type': 'podcast' if 'podcast' in href.lower() else 'article'
                    })
            
            print(f"Found {len(article_links)} articles")
            page_num += 1
        
        return articles
    
    async def scrape_article(self, url: str) -> Optional[Dict]:
        """Scrape a single article."""
        print(f"Scraping: {url}")
        
        await self.page.goto(url)
        await self.page.wait_for_load_state('networkidle')
        
        content = await self.page.content()
        soup = BeautifulSoup(content, 'html.parser')
        
        # Extract title
        title_elem = soup.select_one('h1.entry-title, h1.post-title, h1')
        title = title_elem.get_text(strip=True) if title_elem else "Unknown"
        
        # Extract content
        content_elem = soup.select_one('.entry-content, .post-content, article, main')
        if not content_elem:
            print("Could not find content")
            return None
        
        # Extract date
        date_elem = soup.select_one('time, .published, .post-date')
        date = date_elem.get('datetime', date_elem.get_text(strip=True)) if date_elem else None
        
        return {
            'url': url,
            'title': title,
            'date': date,
            'author': 'Ben Thompson',
            'content_html': str(content_elem),
            'content_text': content_elem.get_text(separator='\n\n', strip=True),
            'scraped_at': datetime.now().isoformat()
        }
    
    async def close(self):
        """Close the browser."""
        if self.browser:
            await self.browser.close()
    
    def save_content(self, content: Dict, filename: str):
        """Save content to file."""
        filepath = os.path.join(self.output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(content, f, indent=2, ensure_ascii=False)
        print(f"Saved to {filepath}")


async def main():
    """Run the scraper."""
    scraper = StratecheryScraper()
    
    try:
        # Start browser (will load saved auth if available)
        has_saved_auth = await scraper.start(headless=False)  # Set True for headless
        
        # If not logged in, perform login
        if not has_saved_auth:
            if not await scraper.login():
                print("Failed to login")
                return
        
        # Interactive menu
        while True:
            print("\n=== Stratechery Scraper ===")
            print("1. Explore current page structure")
            print("2. Scrape archive (list articles)")
            print("3. Scrape specific article")
            print("4. Clear saved authentication")
            print("5. Exit")
            
            choice = input("\nEnter choice (1-5): ").strip()
            
            if choice == '1':
                await scraper.explore_structure()
                input("\nPress Enter to continue...")
                
            elif choice == '2':
                max_pages = input("How many archive pages to scrape? (Enter for all): ").strip()
                max_pages = int(max_pages) if max_pages else None
                
                articles = await scraper.scrape_archive(max_pages=max_pages)
                print(f"\nFound {len(articles)} total articles")
                
                # Ask to save list
                if input("Save article list? (y/n): ").lower() == 'y':
                    scraper.save_content({
                        'articles': articles,
                        'scraped_at': datetime.now().isoformat()
                    }, 'article_list.json')
                
                # Ask to scrape full articles
                num = input(f"How many full articles to scrape? (0-{len(articles)}): ").strip()
                if num and int(num) > 0:
                    for i, article in enumerate(articles[:int(num)]):
                        print(f"\nScraping {i+1}/{num}: {article['title']}")
                        article_data = await scraper.scrape_article(article['url'])
                        if article_data:
                            filename = f"{article['title'][:50].replace('/', '_')}.json"
                            scraper.save_content(article_data, filename)
                        await asyncio.sleep(2)  # Rate limit
                        
            elif choice == '3':
                url = input("Enter article URL: ").strip()
                if url:
                    article_data = await scraper.scrape_article(url)
                    if article_data:
                        filename = f"{article_data['title'][:50].replace('/', '_')}.json"
                        scraper.save_content(article_data, filename)
                        
            elif choice == '4':
                await scraper.clear_auth()
                print("You'll need to login again next time")
                
            elif choice == '5':
                break
                
            else:
                print("Invalid choice")
    
    finally:
        await scraper.close()


if __name__ == '__main__':
    asyncio.run(main())