# Training Data Repository

This repository contains comprehensive training data with detailed per-split metrics, workout data, and wellness information in structured daily files sourced from Garmin Connect.

## Overview

The system automatically scrapes workout and wellness data from Garmin Connect and formats it into human-readable daily Markdown files with structured YAML front matter. Each daily file contains:

- **Sleep Metrics**: Total sleep, sleep stages (deep, light, REM), sleep score, resting heart rate, HRV
- **Daily Metrics**: Step count, body battery charge/drain, resting heart rate  
- **Workout Details**: Distance, time, elevation, heart rate zones, pace, detailed split-by-split data
- **Enhanced Data**: Running dynamics (cadence, stride length, vertical oscillation, ground contact time)

## Data Structure

```
data/
├── index.json          # Complete dataset index for programmatic access
└── YYYY/
    └── MM/
        └── DD.md      # Daily training file with YAML + Markdown
```

## Core Scripts

### Data Collection & Processing

- **`scripts/garmin_scraper.py`** - Main scraper that authenticates with Garmin Connect and retrieves activity and wellness data
- **`scripts/garmin_renderer.py`** - Processes scraped data and generates structured daily Markdown files  
- **`scripts/add_structured_human_readable.py`** - Formats existing daily files with enhanced human-readable sections
- **`scripts/fix_data_consistency.py`** - Comprehensive data consistency fixer that ensures data quality and completeness

### Data Consistency Features

The consistency fixer performs automated corrections across all training files:

- **Missing Splits Recovery**: Re-parses FIT files to populate missing mile splits with full metrics
- **YAML/JSON Synchronization**: Ensures front-matter data exactly matches JSON detail blocks  
- **Unit Standardization**: Converts units consistently (`_mi`, `_ft`, `_in`, `_s`, `_pct` suffixes)
- **Wellness Data Backfill**: Retrieves missing steps, heart rate, HRV, and body battery data from Garmin
- **Weather Data Integration**: Replaces placeholder temperatures with real Visual Crossing API data
- **Index Regeneration**: Automatically rebuilds the complete data index file
- **Data Validation**: Ensures all files meet quality standards and reports any issues

### Configuration

The scraper reads Garmin Connect credentials from environment variables [[memory:2514432]]. Create a `.env` file:

```
GARMIN_EMAIL=your_email@example.com
GARMIN_PASSWORD=your_password
VISUAL_CROSSING_API_KEY=your_weather_api_key  # Optional for weather data
```

## Usage

### Scrape New Data
```bash
npm run scrape-garmin
```

### Generate Daily Files  
```bash
npm run render-garmin
```

### Fix Data Consistency
```bash
npm run fix-data
```

### Update Formatting
```bash
python3 scripts/add_structured_human_readable.py
```

## Data Format

Each daily file contains:
- **YAML Front Matter**: Structured data for programmatic access
- **Human-Readable Summary**: Basic totals and sleep overview
- **Detailed Sections**: Sleep metrics, daily metrics, workout details with split-by-split data
- **Full JSON**: Complete raw data in collapsible section

## Features

- **Accurate Step Data**: Real step counts from Garmin devices (not calculated estimates)
- **Detailed Split Analysis**: Mile-by-mile pace, heart rate, elevation, and running dynamics
- **Sleep & Recovery**: Comprehensive sleep stage analysis and recovery metrics
- **Weather Integration**: Temperature data interpolated across workout splits
- **Body Battery**: Garmin's energy level tracking throughout the day
- **Data Quality Assurance**: Automated consistency checks and corrections 