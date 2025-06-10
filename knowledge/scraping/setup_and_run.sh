#!/bin/bash

echo "Setting up Stratechery scraper..."

# Make sure we're in the knowledge directory
cd ..

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
else
    echo "Creating virtual environment..."
    python3 -m venv venv
    source venv/bin/activate
fi

# Install/upgrade dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Install Playwright browsers
echo "Installing Playwright browsers..."
playwright install chromium

echo ""
echo "Setup complete! Now you can run:"
echo ""
echo "1. Set your credentials:"
echo "   export STRATECHERY_EMAIL='your-email@example.com'"
echo "   export STRATECHERY_PASSWORD='your-password'"
echo ""
echo "2. Run the scraper:"
echo "   cd scraping"
echo "   python stratechery_scraper.py"
echo ""
echo "The scraper will:"
echo "- Open a browser window"
echo "- Let you navigate and press Enter to analyze page structure"
echo "- Press Ctrl+C when ready to start actual scraping"