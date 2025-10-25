# BirdCast Data Scraper

A comprehensive Python scraping system that collects migration data from the [BirdCast dashboard](https://dashboard.birdcast.info/) for counties across major North American bird migration flyways. The system includes scrapers for core counties and all three major flyway corridors (Atlantic, Pacific, and Mississippi).

## Features

- **Multi-Flyway Coverage**: Scrapes data from hundreds of counties across all three major North American flyways
- **Core County Monitoring**: Dedicated scraper for 5 key counties (Florida, Colorado, New Jersey, California, and Alabama)
- **Comprehensive Data Collection**: Captures key migration metrics including:
  - Total birds count
  - Peak migration traffic (birds in flight, direction, speed, altitude)
  - Migration timing (start/end times)
  - Date information
- **Multiple Output Formats**: Saves data to both CSV and JSON formats
- **Automated Scheduling**: Daily execution using macOS launchd for reliability
- **Organized Structure**: Clean separation of scripts, data, logs, and automation files
- **Comprehensive Logging**: Detailed logging for monitoring and troubleshooting
- **Error Handling**: Robust retry logic and error recovery

## Project Structure

```
birdcast-data-grabber/
├── scripts/                    # All scraper scripts
│   ├── birdcast_scraper.py    # Core 5-county scraper
│   ├── atlantic_flyway_scraper.py
│   ├── pacific_flyway_scraper.py
│   └── mississippi_flyway_scraper.py
├── data/                      # All output data files
│   ├── *.csv                  # CSV output files
│   ├── *.json                 # JSON output files
│   └── *_counties_with_urls.csv  # County URL lists
├── logs/                      # All log files
│   ├── *.log                  # Scraper logs
│   └── *_launchd*.log        # Automation logs
├── automation/                # macOS launchd configuration
│   ├── *.plist               # Launch daemon files
│   └── README.md             # Automation documentation
├── archive_scripts/           # Historical/utility scripts
└── venv/                     # Python virtual environment
```

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

### Manual Test Runs

To test individual scrapers:

```bash
# Core 5-county scraper
python scripts/birdcast_scraper.py --test

# Atlantic Flyway scraper
python scripts/atlantic_flyway_scraper.py --test

# Pacific Flyway scraper
python scripts/pacific_flyway_scraper.py --test

# Mississippi Flyway scraper
python scripts/mississippi_flyway_scraper.py --test
```

### Automated Daily Execution

The system uses macOS launchd for reliable daily automation:

- **Core Scraper**: 12:00 PM ET daily
- **Atlantic Flyway**: 12:30 PM ET daily
- **Pacific Flyway**: 1:00 PM ET daily
- **Mississippi Flyway**: 1:30 PM ET daily

See the `automation/README.md` for installation and management instructions.

## Output Files

The system generates organized output files in the `data/` and `logs/` directories:

### Data Files (`data/` directory)
- **Core Counties**: `birdcast_data.csv` and `birdcast_data.json`
- **Atlantic Flyway**: `atlantic_flyway_corridor.json`
- **Pacific Flyway**: `pacific_flyway_corridor.json`
- **Mississippi Flyway**: `mississippi_flyway_corridor.json`
- **County Lists**: `*_flyway_corridor_counties_with_urls.csv`

### Log Files (`logs/` directory)
- **Scraper Logs**: `*_scraper.log` files for each scraper
- **Automation Logs**: `*_launchd.log` and `*_launchd_error.log` files

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

## Automation

The system uses macOS launchd for reliable automation. All automation files are located in the `automation/` directory.

### Installation

Install all scrapers to run automatically:

```bash
# Install all launchd jobs
cd automation
./install_all.sh

# Or install individually
launchctl load ~/Library/LaunchAgents/com.davidjcox.birdcast-scraper.plist
launchctl load ~/Library/LaunchAgents/com.davidjcox.atlantic-flyway-scraper.plist
launchctl load ~/Library/LaunchAgents/com.davidjcox.pacific-flyway-scraper.plist
launchctl load ~/Library/LaunchAgents/com.davidjcox.mississippi-flyway-scraper.plist
```

### Management

```bash
# Check status
launchctl list | grep -E "(birdcast|atlantic|pacific|mississippi)"

# Uninstall
cd automation
./uninstall_all.sh
```

For detailed automation documentation, see `automation/README.md`.

## Troubleshooting

- **Check Log Files**: All logs are in the `logs/` directory
  - `*_scraper.log` - Individual scraper logs
  - `*_launchd.log` - Automation execution logs
  - `*_launchd_error.log` - Automation error logs
- **Network Issues**: Ensure stable internet connection
- **Website Changes**: BirdCast website structure may change, requiring scraper updates
- **Automation Issues**: 
  - Check launchd job status: `launchctl list | grep birdcast`
  - Verify file paths in `.plist` files match your system
  - Ensure Python virtual environment is properly configured

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

### Testing Changes

Test all scrapers after making changes:
```bash
source venv/bin/activate
python scripts/birdcast_scraper.py --test
python scripts/atlantic_flyway_scraper.py --test
python scripts/pacific_flyway_scraper.py --test
python scripts/mississippi_flyway_scraper.py --test
```

### Virtual Environment

Always use the virtual environment when developing:
```bash
# Activate (do this each time you start working)
source venv/bin/activate

# Deactivate when done
deactivate
```

## System Coverage

### Core Counties (5 counties)
- **Duval County, FL** - Jacksonville area
- **Boulder County, CO** - Boulder/Denver area  
- **Essex County, NJ** - Newark area
- **Contra Costa County, CA** - San Francisco Bay area
- **Lee County, AL** - Auburn area

### Flyway Coverage
- **Atlantic Flyway**: ~200+ counties along the Eastern seaboard
- **Pacific Flyway**: ~300+ counties along the Western coast and mountain regions
- **Mississippi Flyway**: ~400+ counties along the central migration corridor

## Notes

- **Respectful Scraping**: All scrapers include appropriate delays and respectful request patterns
- **Data Persistence**: Data is appended to files, preserving historical records
- **Error Handling**: Comprehensive retry logic and error recovery mechanisms
- **Browser Simulation**: User-Agent headers simulate standard browser requests
- **Virtual Environment**: Always use the virtual environment to avoid dependency conflicts
- **Staggered Execution**: Flyway scrapers run 30 minutes apart to avoid server overload
