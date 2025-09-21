#!/usr/bin/env python3
"""
BirdCast Data Scraper
Scrapes migration data from the BirdCast dashboard for Duval County, Florida, and BOulder County, Colorado
"""

import requests
from bs4 import BeautifulSoup
import json
import csv
import os
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
        logging.FileHandler('birdcast_scraper.log'),
        logging.StreamHandler()
    ]
)

class BirdCastScraper:
    def __init__(self, urls=None):
        # Default regions: Duval County, FL and Boulder County, CO
        if urls is None:
            urls = [
                "https://dashboard.birdcast.info/region/US-FL-031",  # Duval County, Florida
                "https://dashboard.birdcast.info/region/US-CO-013"   # Boulder County, Colorado
            ]
        self.urls = urls if isinstance(urls, list) else [urls]
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
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
                starting_fallback = re.search(r'Starting[:\s]*([^,\n\r]+?(?:AM|PM|EDT|EST|MDT|MST|PDT|PST|CDT|CST))', text_content, re.IGNORECASE)
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
                ending_fallback = re.search(r'Ending[:\s]*([^,\n\r]+?(?:AM|PM|EDT|EST|MDT|MST|PDT|PST|CDT|CST))', text_content, re.IGNORECASE)
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
                logging.info(f"Successfully scraped data from {url}: {data}")
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
        """Scrape migration data from all configured BirdCast dashboard URLs"""
        all_data = []
        
        for url in self.urls:
            data = self.scrape_single_url(url)
            if data:
                all_data.append(data)
        
        return all_data
    
    def save_to_csv(self, data_list, filename='birdcast_data.csv'):
        """Save data to CSV file"""
        if not data_list:
            return
        
        # Handle both single data dict and list of data dicts
        if isinstance(data_list, dict):
            data_list = [data_list]
            
        file_exists = os.path.isfile(filename)
        
        # Get all unique fieldnames from all records
        all_fieldnames = set()
        for data in data_list:
            all_fieldnames.update(data.keys())
        
        with open(filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=sorted(all_fieldnames))
            
            if not file_exists:
                writer.writeheader()
            
            for data in data_list:
                writer.writerow(data)
        
        logging.info(f"Data for {len(data_list)} region(s) saved to {filename}")
    
    def save_to_json(self, data_list, filename='birdcast_data.json'):
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
        
        logging.info(f"Data for {len(data_list)} region(s) saved to {filename}")

def run_scraper():
    """Run the scraper and save data"""
    scraper = BirdCastScraper()
    data = scraper.scrape_data()
    
    if data:
        # Save to both CSV and JSON
        scraper.save_to_csv(data)
        scraper.save_to_json(data)
        
        # Print summary for email notification
        print("BirdCast Data Scraper - SUCCESS")
        print("=" * 50)
        print(f"Scraped data for {len(data)} regions at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        for region_data in data:
            region_name = region_data.get('region_name', 'Unknown Region')
            total_birds = region_data.get('total_birds', 'N/A')
            peak_birds = region_data.get('peak_birds_in_flight', 'N/A')
            direction = region_data.get('flight_direction', 'N/A')
            
            print(f"\n{region_name}:")
            print(f"   Total birds: {total_birds:,}" if isinstance(total_birds, int) else f"   Total birds: {total_birds}")
            print(f"   Peak in flight: {peak_birds:,}" if isinstance(peak_birds, int) else f"   Peak in flight: {peak_birds}")
            print(f"   Direction: {direction}")
        
        print(f"\nData saved to: birdcast_data.csv & birdcast_data.json")
        print("=" * 50)
        
        logging.info("Scraping completed successfully")
    else:
        print("BirdCast Data Scraper - FAILED")
        print("No data was collected. Check the logs for details.")
        logging.error("Scraping failed")

def schedule_daily_scraping():
    """Schedule the scraper to run daily at 12:00 PM (noon)"""
    schedule.every().day.at("12:00").do(run_scraper)
    logging.info("Scheduler started - will run daily at 12:00 PM (noon)")
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--schedule":
        # Run in scheduled mode
        schedule_daily_scraping()
    elif len(sys.argv) > 1 and sys.argv[1] == "--test":
        # Run once for testing
        logging.info("Running test scrape...")
        run_scraper()
    else:
        print("BirdCast Data Scraper")
        print("Usage:")
        print("  python birdcast_scraper.py --test      # Run once for testing")
        print("  python birdcast_scraper.py --schedule  # Run daily at 12:00 PM (noon)")
