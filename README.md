# BirdCast Data Scraper

A Python script that scrapes migration data from the [BirdCast dashboard](https://dashboard.birdcast.info/region/US-FL-031) for Duval County, Florida and saves it to CSV and JSON files.

## Features

- Scrapes key migration metrics including:
  - Total birds count
  - Peak migration traffic (birds in flight, direction, speed, altitude)
  - Migration timing (start/end times)
  - Date information
- Saves data to both CSV and JSON formats
- Scheduled daily execution at 12:00 PM (noon)
- Comprehensive logging
- Error handling and retry logic

## Installation

### Development Setup

1. Clone the repository:
```bash
git clone https://github.com/david-j-cox/birdcast-migration-scraper.git
cd birdcast-migration-scraper
```

2. Create and activate a Python virtual environment:
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required dependencies:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Production Installation

If you just want to run the scraper without development:

1. Download or clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Test Run (Run Once)

To test the scraper and run it once:

```bash
python birdcast_scraper.py --test
```

### Scheduled Daily Execution

To run the scraper daily at 12:00 PM (noon):

```bash
python birdcast_scraper.py --schedule
```

This will start a persistent process that runs the scraper every day at 12:00 PM (noon). Keep the terminal window open or run it in the background.

### Running in Background (macOS/Linux)

To run the scheduled scraper in the background:

```bash
nohup python birdcast_scraper.py --schedule > scraper_output.log 2>&1 &
```

## Output Files

The scraper creates several files:

- `birdcast_data.csv` - CSV file with all scraped data (one row per scrape)
- `birdcast_data.json` - JSON file with all scraped data (array of objects)
- `birdcast_scraper.log` - Log file with scraping activity and any errors

## Data Fields

Each scrape captures the following data:

- `scrape_timestamp` - When the data was scraped (ISO format)
- `url` - The URL that was scraped
- `total_birds` - Total number of birds that crossed the region
- `peak_birds_in_flight` - Peak number of birds in flight
- `flight_direction` - Flight direction (e.g., "SSW")
- `flight_speed_mph` - Flight speed in mph
- `flight_altitude_ft` - Flight altitude in feet
- `migration_start` - Migration period start time
- `migration_end` - Migration period end time
- `migration_date` - The date/night of migration

## Automation Options

### Using cron (macOS/Linux)

Add to your crontab to run daily at 12:00 PM (noon):

```bash
crontab -e
```

Add this line (replace with your actual path):
```
0 12 * * * cd /Users/yourusername/path/to/birdcast-data-grabber && python3 birdcast_scraper.py --test >> scraper_cron.log 2>&1
```

### Using launchd (macOS)

Create a plist file for more robust scheduling on macOS.

## Troubleshooting

- Check the `birdcast_scraper.log` file for error messages
- Ensure you have a stable internet connection
- The BirdCast website structure may change, requiring updates to the scraper
- If running scheduled mode, make sure your computer doesn't go to sleep

## Development Workflow

This project uses a standard Git workflow with two main branches:

- **main**: Stable, production-ready code
- **dev**: Development branch for new features and changes

### Contributing

1. Make sure you're on the dev branch:
```bash
git checkout dev
git pull origin dev
```

2. Make your changes and test them:
```bash
source venv/bin/activate  # Activate virtual environment
python birdcast_scraper.py --test
```

3. Commit and push your changes:
```bash
git add .
git commit -m "Description of your changes"
git push origin dev
```

4. When ready for production, merge dev into main via pull request

### Virtual Environment

Always use the virtual environment when developing:
```bash
# Activate (do this each time you start working)
source venv/bin/activate

# Deactivate when done
deactivate
```

## Notes

- The scraper is designed to be respectful of the BirdCast website
- Data is appended to files, so historical data is preserved
- The script includes appropriate delays and error handling
- User-Agent header is set to identify as a standard browser
- Always work in the virtual environment to avoid dependency conflicts
