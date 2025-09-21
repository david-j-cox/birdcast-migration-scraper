#!/bin/bash

# BirdCast Migration Scraper - Development Environment Setup Script
# This script sets up the development environment for the BirdCast scraper

echo "Setting up BirdCast Migration Scraper development environment..."
echo

# Check if Python 3 is installed
if ! command -v python3 &> /dev/null; then
    echo "Python 3 is not installed. Please install Python 3.8 or higher."
    exit 1
fi

echo "Python 3 found: $(python3 --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    echo "Virtual environment created"
else
    echo "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

echo
echo "Development environment setup complete!"
echo
echo "To get started:"
echo "  1. Activate the virtual environment: source venv/bin/activate"
echo "  2. Test the scraper: python birdcast_scraper.py --test"
echo "  3. Check out the dev branch: git checkout dev"
echo
echo "Happy coding!"
echo
