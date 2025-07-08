# Training Data

This repository contains comprehensive training data with detailed per-split metrics, workout data, and wellness information in structured daily files.

## Data Structure for AI Navigation

Each daily file follows this structured format:

```yaml
---
date: 2025-07-07
schema: 2

sleep_metrics:
  sleep_minutes: 412
  deep_minutes: 92
  light_minutes: 246
  rem_minutes: 94
  awake_minutes: 30
  sleep_score: 82
  resting_hr: 53
  hrv_night_avg: 46

daily_metrics:
  body_battery:
    charge: 52
    drain: 65
  steps: 10234
  total_workout_distance_mi: 5.60
  total_moving_time_s: 3600
  total_elev_gain_ft: 150

workout_metrics:
  - id: 987654321
    type: Run
    start: "2025-07-07T06:00:00-05:00"
    distance_mi: 2.83
    moving_time_s: 1483
    elev_gain_ft: 33
    avg_hr: 158
    max_hr: 169
    avg_pace_s_per_mi: 740
    splits:
      - mile: 1
        avg_hr: 158
        max_hr: 163
        avg_pace_s_per_mi: 740
        mile_time_s: 740
        elev_gain_ft: 8
---
# 2025-07-07 · Daily Summary
**Totals:** 5.6 mi • 1 h 0 m • 150 ft ↑ • 10,234 steps
**Sleep:** 6 h 52 m (Score 82) • Rest HR 53 bpm • HRV 46 ms • BB +52/–65

<details>
<summary>Full JSON</summary>
```json
{ ... full JSON data ... }
```
</details>
```

## Recent Activities

- **[Monday, July 07, 2025](data/2025/07/07.md)** - 1 workout, 8.0 miles
- **[Sunday, July 06, 2025](data/2025/07/06.md)** - 1 workout, 2.0 miles
- **[Friday, July 04, 2025](data/2025/07/04.md)** - 1 workout, 3.9 miles
- **[Wednesday, July 02, 2025](data/2025/07/02.md)** - 1 workout, 2.8 miles
- **[Tuesday, July 01, 2025](data/2025/07/01.md)** - 2 workouts, 3.3 miles
- **[Sunday, June 29, 2025](data/2025/06/29.md)** - 1 workout, 3.5 miles
- **[Saturday, June 28, 2025](data/2025/06/28.md)** - 1 workout, 7.0 miles
- **[Thursday, June 26, 2025](data/2025/06/26.md)** - 1 workout, 2.0 miles
- **[Wednesday, June 25, 2025](data/2025/06/25.md)** - 1 workout, 3.0 miles
- **[Tuesday, June 24, 2025](data/2025/06/24.md)** - 2 workouts, 3.7 miles

## Data Index

The complete dataset is available via [data/index.json](data/index.json) containing all 43 daily training files from March through July 2025, organized by date with metadata for programmatic access.

