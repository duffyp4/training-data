# Training Data - Enhanced Format

This repository contains daily training data in an enhanced format with detailed metrics, 
unit conversions, and comprehensive workout analysis.

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

## Directory Structure

```
data/
├── YYYY/
│   ├── MM/
│   │   ├── DD.md (daily summary with YAML frontmatter)
│   │   └── ...
│   └── ...
└── ...
```

## Schema Version 2 Features

- **Enhanced Metrics**: HR zones, running dynamics, recovery data
- **Clean Units**: Standardized to feet, inches, seconds, miles
- **Weather Interpolation**: Per-split temperature data
- **Daily Summaries**: Sleep, HRV, body battery, step count
- **Detailed Splits**: Mile-by-mile analysis with power and form metrics

## Data Sources

- **Garmin Connect**: Primary activity and wellness data
- **FIT Files**: Detailed per-second metrics and running dynamics
- **Weather APIs**: Historical temperature and conditions
