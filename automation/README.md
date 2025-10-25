# Automation Configuration

This folder contains all the launchd plist files for automated BirdCast data scraping.

## Active Scheduled Jobs:

### `com.davidjcox.birdcast-scraper.plist`
- **Schedule**: Daily at 12:00 PM ET
- **Script**: `scripts/birdcast_scraper.py`
- **Purpose**: Scrapes 5 core counties (FL, CO, NJ, CA, AL)
- **Output**: `data/birdcast_data.json`
- **Duration**: ~30 seconds

### `com.davidjcox.atlantic-flyway-scraper.plist`
- **Schedule**: Daily at 12:30 PM ET
- **Script**: `scripts/atlantic_flyway_scraper.py`
- **Purpose**: Scrapes ~275 Atlantic Flyway corridor counties
- **Output**: `data/atlantic_flyway_corridor.json`
- **Duration**: ~2-3 minutes

### `com.davidjcox.pacific-flyway-scraper.plist`
- **Schedule**: Daily at 1:00 PM ET
- **Script**: `scripts/pacific_flyway_scraper.py`
- **Purpose**: Scrapes Pacific Flyway corridor counties (AK, CA, OR, WA, etc.)
- **Output**: `data/pacific_flyway_corridor.json`
- **Duration**: ~2-3 minutes

### `com.davidjcox.mississippi-flyway-scraper.plist`
- **Schedule**: Daily at 1:30 PM ET
- **Script**: `scripts/mississippi_flyway_scraper.py`
- **Purpose**: Scrapes Mississippi Flyway corridor counties (MN, WI, IA, IL, MO, AR, LA, MS, TN, etc.)
- **Output**: `data/mississippi_flyway_corridor.json`
- **Duration**: ~2-3 minutes

## Installation Commands:

To install/reinstall these launchd jobs:

```bash
# Copy plist files to LaunchAgents
cp automation/*.plist ~/Library/LaunchAgents/

# Load all jobs
launchctl load ~/Library/LaunchAgents/com.davidjcox.birdcast-scraper.plist
launchctl load ~/Library/LaunchAgents/com.davidjcox.atlantic-flyway-scraper.plist
launchctl load ~/Library/LaunchAgents/com.davidjcox.pacific-flyway-scraper.plist
launchctl load ~/Library/LaunchAgents/com.davidjcox.mississippi-flyway-scraper.plist
```

## Management Commands:

```bash
# Check status of all jobs
launchctl list | grep -E "(birdcast|atlantic|pacific|mississippi)"

# Unload a job (replace with specific job name)
launchctl unload ~/Library/LaunchAgents/com.davidjcox.birdcast-scraper.plist

# Manually trigger a job
launchctl start com.davidjcox.birdcast-scraper
```

## Log Files:

All output logs are stored in the `logs/` folder:
- `logs/scraper_launchd.log` - Core scraper output
- `logs/atlantic_flyway_launchd.log` - Atlantic Flyway output
- `logs/pacific_flyway_launchd.log` - Pacific Flyway output
- `logs/mississippi_flyway_launchd.log` - Mississippi Flyway output
- Individual scraper logs also available in `logs/`
