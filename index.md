# Training Data - Enhanced Daily Files

This repository contains comprehensive training data with detailed per-split metrics, 
weather interpolation, and Garmin wellness data in organized daily files.

## Recent Activities

- **[Tuesday, July 01, 2025](data/2025/07/01.md)** - 2 workouts, 3.3 miles
- **[Sunday, June 29, 2025](data/2025/06/29.md)** - 1 workout, 3.5 miles
- **[Saturday, June 28, 2025](data/2025/06/28.md)** - 1 workout, 7.0 miles
- **[Thursday, June 26, 2025](data/2025/06/26.md)** - 1 workout, 2.0 miles
- **[Wednesday, June 25, 2025](data/2025/06/25.md)** - 1 workout, 3.0 miles
- **[Tuesday, June 24, 2025](data/2025/06/24.md)** - 2 workouts, 3.7 miles
- **[Monday, June 23, 2025](data/2025/06/23.md)** - 1 workout, 2.0 miles
- **[Saturday, June 21, 2025](data/2025/06/21.md)** - 1 workout, 2.8 miles
- **[Friday, June 20, 2025](data/2025/06/20.md)** - 1 workout, 6.0 miles
- **[Sunday, June 15, 2025](data/2025/06/15.md)** - 1 workout, 2.2 miles
- **[Saturday, June 14, 2025](data/2025/06/14.md)** - 1 workout, 5.0 miles
- **[Friday, June 13, 2025](data/2025/06/13.md)** - 1 workout, 2.3 miles
- **[Wednesday, June 11, 2025](data/2025/06/11.md)** - 1 workout, 2.4 miles
- **[Tuesday, June 10, 2025](data/2025/06/10.md)** - 1 workout, 2.9 miles
- **[Monday, June 09, 2025](data/2025/06/09.md)** - 1 workout, 1.8 miles

## Browse Historical Data

### 📅 By Month
- **[July 2025](data/2025/07/)** - 2 workouts, 3.3 miles
- **[June 2025](data/2025/06/)** - 19 workouts, 46.8 miles  
- **[May 2025](data/2025/05/)** - 6 workouts, 13.7 miles
- **[April 2025](data/2025/04/)** - 7 workouts, 18.1 miles
- **[March 2025](data/2025/03/)** - 8 workouts, 19.5 miles

### 🗂️ Directory Structure
```
data/2025/
├── 03/ → March (8 activities: 08, 12, 18, 20, 21, 24, 28, 29)
├── 04/ → April (7 activities: 02, 06, 08, 12, 14, 24, 30)
├── 05/ → May (6 activities: 04, 06, 07, 19, 27, 29)
├── 06/ → June (17 activities: 02, 03, 07, 09, 10, 11, 13, 14, 15, 20, 21, 23, 24, 25, 26, 28, 29)
└── 07/ → July (1 activity: 01)
```

### 🚀 Quick Links
- **[First Activity](data/2025/03/08.md)** (March 8, 2025)
- **[Latest Activity](data/2025/07/01.md)** (July 1, 2025)
- **[Longest Run](data/2025/06/28.md)** (7.0 miles - June 28)
- **[All 2025 Data](data/2025/)** (Browse folders directly)


## Enhanced Features

- **📊 Detailed Splits**: Per-mile HR, pace, cadence, stride, power, weather
- **🌤️ Real Weather**: Historical temperature data via Visual Crossing API
- **😴 Wellness Data**: Sleep stages, HRV, body battery, resting HR
- **🏃 Running Dynamics**: GCT, vertical oscillation, power, balance
- **📁 Organized Structure**: Daily files with YAML frontmatter
- **🔄 Automated Collection**: Nightly sync with latest Garmin data

## Directory Structure

```
data/
├── YYYY/
│   ├── MM/
│   │   ├── DD.md (enhanced daily summary)
│   │   └── ...
│   └── ...
└── ...
```

## Schema Version 2

Each daily file contains:
- **daily_metrics**: Sleep, HRV, steps, totals
- **workout_metrics**: Enhanced workouts with detailed splits
- **Front matter**: YAML for easy parsing
- **Weather data**: Real historical temperatures per split
- **Multiple workouts**: Support for multi-workout days

## Data Sources

- **Garmin Connect**: Primary activity and wellness data
- **Visual Crossing**: Historical weather and temperature data
- **FIT Files**: Detailed per-second metrics and running dynamics

