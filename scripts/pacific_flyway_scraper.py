#!/usr/bin/env python3
"""
Pacific Flyway BirdCast Data Scraper
Scrapes migration data from the BirdCast dashboard for all counties along the Pacific Flyway corridor
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
import pandas as pd
from datetime import datetime, timezone
import re
import time
import schedule
import logging
from dateutil import parser as date_parser
import pytz

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/pacific_flyway_scraper.log'),
        logging.StreamHandler()
    ]
)

class PacificFlywayBirdCastScraper:
    def __init__(self, urls=None):
        if urls is None:
            # Load URLs from the Pacific Flyway corridor analysis
            urls = self.load_flyway_urls()
        self.urls = urls if isinstance(urls, list) else [urls]
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        logging.info(f"Initialized scraper with {len(self.urls)} Pacific Flyway counties")
    
    def load_flyway_urls(self):
        """Load BirdCast URLs from the Pacific Flyway corridor analysis CSV"""
        csv_file = '../data/pacific_flyway_corridor_counties_with_urls.csv'
        if not os.path.exists(csv_file):
            logging.error(f"Pacific Flyway CSV file not found: {csv_file}")
            logging.error("Please run the pacific_flyway_corridor.py script first to generate the county list")
            return []
        
        try:
            df = pd.read_csv(csv_file)
            urls = df['birdcast_url'].tolist()
            logging.info(f"Loaded {len(urls)} BirdCast URLs from Pacific Flyway corridor analysis")
            return urls
        except Exception as e:
            logging.error(f"Error loading URLs from {csv_file}: {e}")
            return []
    
    def parse_datetime_string(self, datetime_str):
        """Parse datetime string from BirdCast into ISO format timestamp"""
        if not datetime_str:
            return None
        
        try:
            # Clean up the string - handle common formats like "Sun, Aug 17, 2025, 8:10 PM EDT"
            cleaned_str = datetime_str.strip()
            
            # Parse the datetime string - dateutil is very flexible
            parsed_dt = date_parser.parse(cleaned_str, fuzzy=True)
            
            # Convert to UTC and return ISO format
            if parsed_dt.tzinfo is None:
                # If no timezone info, assume UTC
                parsed_dt = parsed_dt.replace(tzinfo=timezone.utc)
            else:
                # Convert to UTC
                parsed_dt = parsed_dt.astimezone(timezone.utc)
            
            return parsed_dt.isoformat()
        
        except Exception as e:
            logging.warning(f"Could not parse datetime string '{datetime_str}': {e}")
            return datetime_str  # Return original string if parsing fails
        
    def scrape_single_url(self, url):
        """Scrape migration data from a single BirdCast dashboard URL"""
        try:
            logging.info(f"Scraping data from {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Check if we're getting actual HTML content or just CSS
            content_type = response.headers.get('content-type', '').lower()
            if 'text/html' not in content_type:
                logging.error(f"Unexpected content type: {content_type}")
                return None
            
            html_content = response.text
            
            # Check if we got CSS instead of HTML
            if html_content.strip().startswith('@keyframes') or 'css' in html_content[:100].lower():
                logging.error("Received CSS content instead of HTML - the URL might be incorrect")
                return None
            
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Extract data
            data = {
                'scrape_timestamp': datetime.now(timezone.utc).isoformat(),
                'url': url
            }
            
            # Extract region name from URL and page content
            region_match = re.search(r'/region/([^/]+)$', url)
            if region_match:
                data['region_code'] = region_match.group(1)
            
            # Try to find region name in the page content
            text_content = soup.get_text()
            region_name_match = re.search(r'Migration Dashboard\s+([A-Za-z\s,]+?)(?:\s+Search|$)', text_content)
            if region_name_match:
                data['region_name'] = region_name_match.group(1).strip()
            
            # Try to find "xxx Birds crossed" pattern
            birds_crossed_match = re.search(r'(\d{1,3}(?:,?\d{3})*)\s+Birds crossed.*last night', text_content, re.IGNORECASE)
            if birds_crossed_match:
                data['total_birds'] = int(birds_crossed_match.group(1).replace(',', ''))
            
            # Try to find peak birds in flight
            peak_match = re.search(r'(\d{1,3}(?:,?\d{3})*)\s+Birds in flight', text_content, re.IGNORECASE)
            if peak_match:
                data['peak_birds_in_flight'] = int(peak_match.group(1).replace(',', ''))
            
            # Try to find direction (SSW, NNE, etc.)
            direction_match = re.search(r'Direction[:\s]*([NEWS]{1,3})', text_content, re.IGNORECASE)
            if direction_match:
                data['flight_direction'] = direction_match.group(1)
            
            # Try to find speed
            speed_match = re.search(r'Speed[:\s]*(\d+)\s*mph', text_content, re.IGNORECASE)
            if speed_match:
                data['flight_speed_mph'] = int(speed_match.group(1))
            
            # Try to find altitude  
            altitude_match = re.search(r'Altitude[:\s]*(\d{1,3}(?:,?\d{3})*)\s*ft', text_content, re.IGNORECASE)
            if altitude_match:
                data['flight_altitude_ft'] = int(altitude_match.group(1).replace(',', ''))
            
            # Try to find timing information (handle different time zones)
            # Look for patterns like "Starting: Sun, Aug 17, 2025, 8:00 PM MDT"
            starting_match = re.search(r'Starting[:\s]+([A-Za-z]{3},\s+[A-Za-z]+\s+\d{1,2},\s+\d{4},\s+\d{1,2}:\d{2}\s+[AP]M\s+[A-Z]{3,4})', text_content, re.IGNORECASE)
            if starting_match:
                start_str = starting_match.group(1).strip()
                data['migration_start_raw'] = start_str
                data['migration_start_utc'] = self.parse_datetime_string(start_str)
            else:
                # Fallback to simpler pattern
                starting_fallback = re.search(r'Starting[:\s]*([^,\n\r]+?(?:AM|PM|EDT|EST|MDT|MST|PDT|PST|CDT|CST|AKDT|AKST))', text_content, re.IGNORECASE)
                if starting_fallback:
                    start_str = starting_fallback.group(1).strip()
                    data['migration_start_raw'] = start_str
                    data['migration_start_utc'] = self.parse_datetime_string(start_str)
                
            ending_match = re.search(r'Ending[:\s]+([A-Za-z]{3},\s+[A-Za-z]+\s+\d{1,2},\s+\d{4},\s+\d{1,2}:\d{2}\s+[AP]M\s+[A-Z]{3,4})', text_content, re.IGNORECASE)
            if ending_match:
                end_str = ending_match.group(1).strip()
                data['migration_end_raw'] = end_str
                data['migration_end_utc'] = self.parse_datetime_string(end_str)
            else:
                # Fallback to simpler pattern
                ending_fallback = re.search(r'Ending[:\s]*([^,\n\r]+?(?:AM|PM|EDT|EST|MDT|MST|PDT|PST|CDT|CST|AKDT|AKST))', text_content, re.IGNORECASE)
                if ending_fallback:
                    end_str = ending_fallback.group(1).strip()
                    data['migration_end_raw'] = end_str
                    data['migration_end_utc'] = self.parse_datetime_string(end_str)
            
            # Try to find date information
            date_match = re.search(r'((?:Sunday|Monday|Tuesday|Wednesday|Thursday|Friday|Saturday)\s+night,\s+[A-Za-z]+\s+\d{1,2})', text_content, re.IGNORECASE)
            if date_match:
                data['migration_date'] = date_match.group(1)
            
            # Log what we found
            if len(data) > 2:  # More than just timestamp and URL
                logging.info(f"Successfully scraped data from {url}: found {len(data)-2} data fields")
            else:
                logging.warning(f"No migration data found for {url}")
                # Save a sample of the content for debugging
                data['debug_content_sample'] = text_content[:500] if text_content else "No text content"
            
            return data
            
        except requests.RequestException as e:
            logging.error(f"Request failed for {url}: {e}")
            return None
        except Exception as e:
            logging.error(f"Scraping failed for {url}: {e}")
            return None
    
    def scrape_data(self):
        """Scrape migration data from all Pacific Flyway counties"""
        all_data = []
        
        logging.info(f"Starting to scrape {len(self.urls)} Pacific Flyway counties...")
        
        for i, url in enumerate(self.urls, 1):
            logging.info(f"Progress: {i}/{len(self.urls)} counties")
            data = self.scrape_single_url(url)
            if data:
                all_data.append(data)
            
            # Add a small delay to be respectful to the server
            time.sleep(0.5)
        
        logging.info(f"Completed scraping. Successfully collected data from {len(all_data)} counties")
        return all_data
    
    def save_to_json(self, data_list, filename='../data/pacific_flyway_corridor.json'):
        """Save data to JSON file (append to list)"""
        if not data_list:
            return
        
        # Handle both single data dict and list of data dicts
        if isinstance(data_list, dict):
            data_list = [data_list]
            
        if os.path.isfile(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                try:
                    existing_data = json.load(f)
                except json.JSONDecodeError:
                    existing_data = []
        else:
            existing_data = []
        
        existing_data.extend(data_list)
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(existing_data, f, indent=2, ensure_ascii=False)
        
        logging.info(f"Data for {len(data_list)} Pacific Flyway counties saved to {filename}")

def run_flyway_scraper():
    """Run the Pacific Flyway scraper and save data"""
    scraper = PacificFlywayBirdCastScraper()
    data = scraper.scrape_data()
    
    if data:
        # Save to JSON
        scraper.save_to_json(data)
        
        # Print summary
        print("Pacific Flyway BirdCast Data Scraper - SUCCESS")
        print("=" * 60)
        print(f"Scraped data for {len(data)} counties at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Count by state
        state_counts = {}
        total_birds_by_state = {}
        
        for region_data in data:
            region_name = region_data.get('region_name', 'Unknown Region')
            total_birds = region_data.get('total_birds', 0)
            
            # Extract state from region name
            if ',' in region_name:
                state = region_name.split(',')[-1].strip()
                state_counts[state] = state_counts.get(state, 0) + 1
                if isinstance(total_birds, int):
                    total_birds_by_state[state] = total_birds_by_state.get(state, 0) + total_birds
        
        print(f"\nCounties scraped by state:")
        for state, count in sorted(state_counts.items()):
            total_birds = total_birds_by_state.get(state, 0)
            print(f"   {state}: {count} counties, {total_birds:,} total birds")
        
        print(f"\nData saved to: pacific_flyway_corridor.json")
        print("=" * 60)
        
        logging.info("Pacific Flyway scraping completed successfully")
    else:
        print("Pacific Flyway BirdCast Data Scraper - FAILED")
        print("No data was collected. Check the logs for details.")
        logging.error("Pacific Flyway scraping failed")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Run once for testing
        logging.info("Running test scrape of Pacific Flyway counties...")
        run_flyway_scraper()
    else:
        print("Pacific Flyway BirdCast Data Scraper")
        print("Usage:")
        print("  python pacific_flyway_scraper.py --test      # Run once for testing")
        print("  # Note: This scraper is designed for manual runs due to the large number of counties")
