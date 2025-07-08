# Training Data - Enhanced Format

This repository contains daily training data in an enhanced format with detailed metrics, 
unit conversions, and comprehensive workout analysis.

## Recent Activities

- **[Monday, July 07, 2025](data/2025/07/07.md)** - 1 workout, 8.0 miles
- **[Sunday, July 06, 2025](data/2025/07/06.md)** - 1 workout, 2.0 miles
- **[Friday, July 04, 2025](data/2025/07/04.md)** - 1 workout, 3.9 miles
- **[Wednesday, July 02, 2025](data/2025/07/02.md)** - 1 workout, 2.8 miles
- **[Tuesday, July 01, 2025](data/2025/07/01.md)** - 1 workout, 0.3 miles

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
