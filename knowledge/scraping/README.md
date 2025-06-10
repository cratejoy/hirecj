# Stratechery Scraper

Playwright-based scraper for Stratechery content with persistent authentication (cookie storage).

## Features

- **Cookie Persistence**: Login once, reuse authentication for future runs
- **Interactive Login**: Opens browser for you to login manually (no password storage)
- **Interactive Menu**: Choose what to scrape without code changes
- **Structure Explorer**: Analyze page structure before scraping
- **Rate Limiting**: Respectful scraping with delays
- **Flexible Output**: JSON format for easy processing

## Setup

```bash
./setup_and_run.sh
```

Or manually:
```bash
# From knowledge directory
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

## Usage

```bash
cd scraping
python stratechery_scraper.py
```

### First Run
1. Opens browser window
2. Shows Stratechery login page
3. You login manually with your credentials
4. Scraper detects successful login
5. Saves authentication state for future use
6. Shows interactive menu

### Subsequent Runs
1. Loads saved authentication state
2. Verifies you're still logged in
3. Goes straight to menu (no login needed)

### Menu Options

1. **Explore current page structure**: Analyze HTML structure
2. **Scrape archive**: List articles with option to download
3. **Scrape specific article**: Download single article by URL
4. **Clear saved authentication**: Remove saved cookies
5. **Exit**: Close scraper

## Output

- **Authentication**: `stratechery_auth_state.json` (gitignored)
- **Content**: `stratechery_content/` directory with JSON files
- **Format**: Each article as JSON with HTML and clean text

## Security

- No passwords stored anywhere
- You login interactively in browser
- Only authentication cookies are saved
- Auth state file is gitignored

## Troubleshooting

If auth expires or fails:
1. Use option 4 to clear saved authentication
2. Run again to login fresh