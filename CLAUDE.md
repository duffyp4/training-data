# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Core Operations
- `python3 scripts/garmin_scraper.py` - Scrape Garmin Connect data (requires .env with credentials)
- `python3 scripts/garmin_to_daily_files.py` - Convert activities.json to structured daily files
- `python3 scripts/generate_index.py` - Generate main index page with chronological links
- `pip install -r requirements.txt` - Install Python dependencies

### NPM Scripts (defined in package.json)
- `npm run scrape-garmin` - Run Garmin data scraper
- `npm run render-garmin` - Run Garmin data renderer (legacy)
- `npm run fix-data` - Fix data consistency issues

## Architecture Overview

This is a **Garmin Connect training data scraper and processor** that automatically generates structured daily training files with comprehensive wellness metrics.

### Core Data Flow
1. **garmin_scraper.py** - Primary data collection script using hybrid approach:
   - REST API for wellness metrics (sleep, steps, body battery, resting HR)  
   - FIT file parsing for rich workout data (training effects, HR zones, running dynamics)
   - Outputs raw data to `activities.json`

2. **garmin_to_daily_files.py** - Data processor that converts raw JSON to structured files:
   - Groups activities by date into `data/YYYY/MM/DD.md` files
   - Adds weather integration via Visual Crossing API
   - Converts GPS coordinates to city names
   - Generates YAML front matter + human-readable Markdown sections

3. **generate_index.py** - Creates main index with chronological navigation

### Data Structure
- `data/` - Main data directory organized by year/month/day
- `data/index.json` - Metadata about processed files  
- `data/last_id.json` - Tracks last processed activity ID
- `scripts/` - Python processing scripts
- `backups/` - Historical backups of data files

### Key Dependencies
- **garth 0.5.17+** - Modern Garmin Connect API client with wellness helpers
- **fitparse** - FIT file parsing for detailed workout metrics  
- **Visual Crossing Weather API** - Weather data integration for workouts
- **python-dateutil** - Date/timezone handling

### Authentication Requirements
The system requires a `.env` file with:
- `GARMIN_EMAIL` and `GARMIN_PASSWORD` - Garmin Connect credentials
- `VISUAL_CROSSING_API_KEY` - Weather API key
- Optional: `GARMIN_2FA_SECRET` if 2FA is enabled

### Output Format
Daily files contain YAML front matter with structured metrics plus human-readable Markdown sections covering sleep, wellness, and detailed workout analysis with training effects, running dynamics, and power zones.

### Recent Changes
**2025-07-22**: Fixed AI agent data access issue by updating `generate_index.py` to maintain `data/index.json`. Previously, AI agents could only see training data through July 7th despite having current data through July 21st, because the JSON index was stale. Now both human-readable `index.md` and machine-readable `data/index.json` are kept in sync with all available training files.