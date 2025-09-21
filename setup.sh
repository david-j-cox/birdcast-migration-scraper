#!/bin/bash

# BirdCast Data Scraper Setup Script

echo "Setting up BirdCast Data Scraper..."

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed. Please install Python 3 first."
    exit 1
fi

# Create virtual environment (optional but recommended)
echo "Creating virtual environment..."
python3 -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo "Setup complete!"
echo ""
echo "To run the scraper:"
echo "1. Activate the virtual environment: source venv/bin/activate"
echo "2. Test the scraper: python birdcast_scraper.py --test"
echo "3. Run scheduled: python birdcast_scraper.py --schedule"
