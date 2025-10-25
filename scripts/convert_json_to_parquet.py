#!/usr/bin/env python3
"""
Convert existing JSON data files to Parquet format with deduplication
"""

import json
import pandas as pd
import os
from pathlib import Path
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def convert_json_to_parquet(json_file_path, parquet_file_path):
    """
    Convert JSON file to Parquet format with deduplication
    
    Args:
        json_file_path: Path to the JSON file
        parquet_file_path: Path where the Parquet file should be saved
    
    Returns:
        tuple: (success: bool, records_processed: int, duplicates_removed: int)
    """
    try:
        if not os.path.exists(json_file_path):
            logging.warning(f"JSON file not found: {json_file_path}")
            return False, 0, 0
        
        # Load JSON data
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        if not data:
            logging.warning(f"No data found in {json_file_path}")
            return False, 0, 0
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        original_count = len(df)
        
        # Remove duplicates based on scrape_timestamp and region_code
        # Keep the most recent entry for each region_code + date combination
        if 'scrape_timestamp' in df.columns and 'region_code' in df.columns:
            # Convert scrape_timestamp to datetime for proper sorting
            df['scrape_timestamp_dt'] = pd.to_datetime(df['scrape_timestamp'])
            
            # Sort by timestamp (most recent first) then drop duplicates
            df_sorted = df.sort_values('scrape_timestamp_dt', ascending=False)
            
            # For deduplication, we'll keep the most recent entry per region per day
            # Extract date from migration_date or scrape_timestamp
            if 'migration_date' in df.columns:
                df_sorted['date_key'] = df_sorted['migration_date']
            else:
                df_sorted['date_key'] = df_sorted['scrape_timestamp_dt'].dt.date
            
            # Drop duplicates keeping first (most recent due to sorting)
            df_dedup = df_sorted.drop_duplicates(
                subset=['region_code', 'date_key'], 
                keep='first'
            )
            
            # Remove the helper columns
            df_dedup = df_dedup.drop(['scrape_timestamp_dt', 'date_key'], axis=1)
        else:
            # Fallback: remove exact duplicates
            df_dedup = df.drop_duplicates()
        
        final_count = len(df_dedup)
        duplicates_removed = original_count - final_count
        
        # Optimize data types for better compression
        for col in df_dedup.columns:
            if col in ['total_birds', 'peak_birds_in_flight', 'flight_speed_mph', 'flight_altitude_ft']:
                df_dedup[col] = pd.to_numeric(df_dedup[col], errors='coerce').astype('Int64')
        
        # Save to Parquet with compression
        df_dedup.to_parquet(
            parquet_file_path, 
            compression='snappy',
            index=False
        )
        
        logging.info(f"Converted {json_file_path} to {parquet_file_path}")
        logging.info(f"  Original records: {original_count}")
        logging.info(f"  Final records: {final_count}")
        logging.info(f"  Duplicates removed: {duplicates_removed}")
        
        return True, final_count, duplicates_removed
        
    except Exception as e:
        logging.error(f"Error converting {json_file_path}: {e}")
        return False, 0, 0

def main():
    """Convert all existing JSON files to Parquet format"""
    
    # Define the data directory
    data_dir = Path("/Users/davidjcox/Library/CloudStorage/Dropbox/Miscellaneous/birdcast-data-grabber/data")
    
    # Define JSON to Parquet mappings
    conversions = [
        ("birdcast_data.json", "birdcast_data.parquet"),
        ("atlantic_flyway_corridor.json", "atlantic_flyway_corridor.parquet"),
        ("mississippi_flyway_corridor.json", "mississippi_flyway_corridor.parquet"),
        ("pacific_flyway_corridor.json", "pacific_flyway_corridor.parquet")
    ]
    
    total_processed = 0
    total_duplicates = 0
    successful_conversions = 0
    
    logging.info("Starting JSON to Parquet conversion...")
    
    for json_filename, parquet_filename in conversions:
        json_path = data_dir / json_filename
        parquet_path = data_dir / parquet_filename
        
        success, records, duplicates = convert_json_to_parquet(json_path, parquet_path)
        
        if success:
            successful_conversions += 1
            total_processed += records
            total_duplicates += duplicates
        
    logging.info("Conversion Summary:")
    logging.info(f"  Files converted: {successful_conversions}/{len(conversions)}")
    logging.info(f"  Total records processed: {total_processed}")
    logging.info(f"  Total duplicates removed: {total_duplicates}")
    
    if successful_conversions > 0:
        logging.info("\nNext steps:")
        logging.info("1. Verify the Parquet files contain the expected data")
        logging.info("2. Update your scraper scripts to use Parquet format")
        logging.info("3. Consider backing up and removing the original JSON files")
    
    return successful_conversions == len(conversions)

if __name__ == "__main__":
    success = main()
    if success:
        print("All conversions completed successfully!")
    else:
        print("Some conversions failed. Check the logs for details.")
