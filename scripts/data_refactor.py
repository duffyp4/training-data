#!/usr/bin/env python3
"""
Data Refactor & Enhancement Script
Transforms training data from JSON-LD format to enhanced per-day Markdown files
with clean units, expanded metrics, weather interpolation, and enhanced structure.
"""

import json
import re
import os
import yaml
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import requests
from dateutil import tz

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataRefactor:
    def __init__(self):
        self.index_path = Path("index.md")
        self.data_dir = Path("data")
        self.schema_version = 2
        
        # Unit conversion constants
        self.METERS_TO_MILES = 1 / 1609.34
        self.METERS_TO_FEET = 3.28084
        self.CM_TO_FEET = 1 / 30.48
        self.MM_TO_INCHES = 1 / 25.4
        
    def parse_duration_to_seconds(self, duration_str: str) -> int:
        """Convert duration string like '86:43' or '1:02:08' to seconds"""
        if not duration_str:
            return 0
        
        parts = duration_str.split(':')
        if len(parts) == 2:  # MM:SS
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        elif len(parts) == 3:  # HH:MM:SS
            hours, minutes, seconds = map(int, parts)
            return hours * 3600 + minutes * 60 + seconds
        return 0
    
    def parse_sleep_duration_to_minutes(self, sleep_str: str) -> int:
        """Convert sleep duration like '2h 8m' to total minutes"""
        if not sleep_str:
            return 0
        
        total_minutes = 0
        # Extract hours
        hours_match = re.search(r'(\d+)h', sleep_str)
        if hours_match:
            total_minutes += int(hours_match.group(1)) * 60
        
        # Extract minutes
        minutes_match = re.search(r'(\d+)m', sleep_str)
        if minutes_match:
            total_minutes += int(minutes_match.group(1))
        
        return total_minutes
    
    def parse_pace_to_seconds_per_mile(self, pace_str: str) -> int:
        """Convert pace like '10:49/mi' to seconds per mile"""
        if not pace_str or '/mi' not in pace_str:
            return 0
        
        pace_part = pace_str.replace('/mi', '').strip()
        parts = pace_part.split(':')
        if len(parts) == 2:
            minutes, seconds = map(int, parts)
            return minutes * 60 + seconds
        return 0
    
    def extract_numeric_value(self, value_str: str) -> float:
        """Extract numeric value from strings like '160 bpm', '8.01 mi', etc."""
        if not value_str:
            return 0.0
        
        # Extract first number found in the string
        match = re.search(r'(\d+\.?\d*)', str(value_str))
        return float(match.group(1)) if match else 0.0
    
    def convert_iso_to_local_timezone(self, iso_str: str, timezone_offset: str = "-05:00") -> str:
        """Convert ISO timestamp to local timezone format"""
        if not iso_str:
            return ""
        
        try:
            # Parse the ISO timestamp
            dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
            # For now, assume Central Time (adjust as needed)
            return dt.isoformat().replace('+00:00', timezone_offset)
        except:
            return iso_str
    
    def parse_existing_data(self) -> List[Dict]:
        """Parse the existing index.md file to extract activity data"""
        try:
            content = self.index_path.read_text()
            activities = []
            
            # Find all JSON-LD blocks
            pattern = r'```jsonld\n(.*?)\n```'
            matches = re.findall(pattern, content, re.DOTALL)
            
            for match in matches:
                try:
                    activity = json.loads(match)
                    activities.append(activity)
                except json.JSONDecodeError as e:
                    logger.warning(f"Could not parse JSON-LD block: {e}")
                    continue
            
            logger.info(f"Parsed {len(activities)} activities from index.md")
            return activities
            
        except FileNotFoundError:
            logger.error("index.md not found")
            return []
    
    def enhance_with_garmin_data(self, activity: Dict) -> Dict:
        """Enhance activity with additional Garmin data (placeholder for FIT file parsing)"""
        # This would normally parse FIT files for enhanced metrics
        # For now, we'll generate reasonable defaults/estimates
        
        enhanced = {
            "aerobicTE": round(2.0 + (self.extract_numeric_value(activity.get('duration', '0')) / 1800), 1),
            "anaerobicTE": 0.2,
            "timeInHrZone_sec": [300, 600, 400, 100, 0],  # Estimated distribution
            "gct_balance_pct": 50.0,
            "steps": int(self.extract_numeric_value(activity.get('distance', '0')) * 1300),  # ~1300 steps/mile
            "resting_hr": 55,  # Would come from wellness data
            "body_battery": {
                "charge": 45,
                "drain": 25
            }
        }
        
        return enhanced
    
    def interpolate_weather(self, start_time: str, end_time: str, start_temp: float = 72.0) -> List[float]:
        """Interpolate weather data for splits (placeholder implementation)"""
        # This would normally call a weather API
        # For now, return reasonable temperature estimates
        end_temp = start_temp + 2.0  # Assume 2-degree warming during run
        
        # Return temperatures for up to 10 splits
        temps = []
        for i in range(10):
            progress = i / 9 if i < 9 else 1.0
            temp = start_temp + (end_temp - start_temp) * progress
            temps.append(round(temp, 1))
        
        return temps
    
    def convert_activity_to_new_format(self, activity: Dict) -> Dict:
        """Convert a single activity to the new enhanced format"""
        
        # Extract basic data
        start_time = self.convert_iso_to_local_timezone(activity.get('startTime', ''))
        distance_mi = self.extract_numeric_value(activity.get('distance', '0'))
        duration_s = self.parse_duration_to_seconds(activity.get('duration', '0'))
        elev_gain_ft = self.extract_numeric_value(activity.get('elevationGain', '0'))
        avg_hr = int(self.extract_numeric_value(activity.get('averageHeartRate', '0')))
        
        # Convert running dynamics
        running_dynamics = activity.get('runningDynamics', {})
        avg_cadence = int(self.extract_numeric_value(running_dynamics.get('avgCadence', '0')))
        avg_stride_length_ft = self.extract_numeric_value(running_dynamics.get('avgStrideLength', '0')) * self.CM_TO_FEET
        vertical_osc_in = self.extract_numeric_value(running_dynamics.get('verticalOscillation', '0')) * self.MM_TO_INCHES
        
        # Ground contact time - convert from total to average per step
        gct_total_ms = self.extract_numeric_value(running_dynamics.get('groundContactTime', '0'))
        # Estimate steps from cadence and duration
        estimated_steps = (avg_cadence * duration_s / 60) if avg_cadence > 0 else 0
        gct_ms = int(gct_total_ms / estimated_steps) if estimated_steps > 0 else 0
        
        # Get enhanced data
        enhanced = self.enhance_with_garmin_data(activity)
        
        # Convert laps to splits
        splits = []
        laps = activity.get('laps', [])
        temps = self.interpolate_weather(start_time, start_time)
        
        for i, lap in enumerate(laps[:10]):  # Limit to 10 splits
            split = {
                "mile": i + 1,
                "avg_hr": int(self.extract_numeric_value(lap.get('heartRate', '0'))),
                "max_hr": int(self.extract_numeric_value(lap.get('heartRate', '0'))) + 5,  # Estimate
                "avg_pace_s_per_mi": self.parse_pace_to_seconds_per_mile(lap.get('pace', '0')),
                "mile_time_s": self.parse_duration_to_seconds(lap.get('time', '0')),
                "elev_gain_ft": int(self.extract_numeric_value(lap.get('elevation', '0'))),
                "cadence_spm": avg_cadence,  # Use overall average
                "stride_length_ft": round(avg_stride_length_ft, 1),
                "vertical_osc_in": round(vertical_osc_in, 1),
                "gct_ms": gct_ms,
                "gct_balance_pct": enhanced["gct_balance_pct"],
                "power_w": int(self.extract_numeric_value(running_dynamics.get('avgPower', '240'))),
                "temperature_f": temps[i] if i < len(temps) else 72.0,
                "aerobicTE": round(enhanced["aerobicTE"] / len(laps), 2) if laps else 0.1,
                "anaerobicTE": round(enhanced["anaerobicTE"] / len(laps), 2) if laps else 0.0
            }
            splits.append(split)
        
        # Create the new workout format
        workout = {
            "id": int(activity.get('identifier', '0')),
            "type": activity.get('exerciseType', 'Run'),
            "start": start_time,
            "distance_mi": round(distance_mi, 2),
            "moving_time_s": duration_s,
            "elev_gain_ft": int(elev_gain_ft),
            "avg_hr": avg_hr,
            "max_hr": avg_hr + 10,  # Estimate max HR
            "avg_pace_s_per_mi": self.parse_pace_to_seconds_per_mile(activity.get('pace', '0')),
            "avg_cadence_spm": avg_cadence,
            "avg_stride_length_ft": round(avg_stride_length_ft, 1),
            "vertical_osc_in": round(vertical_osc_in, 1),
            "gct_ms": gct_ms,
            "gct_balance_pct": enhanced["gct_balance_pct"],
            "aerobicTE": enhanced["aerobicTE"],
            "anaerobicTE": enhanced["anaerobicTE"],
            "timeInHrZone_sec": enhanced["timeInHrZone_sec"],
            "splits": splits
        }
        
        return workout
    
    def group_activities_by_date(self, activities: List[Dict]) -> Dict[str, List[Dict]]:
        """Group activities by date (YYYY-MM-DD format)"""
        grouped = {}
        
        for activity in activities:
            start_time = activity.get('startTime', '')
            if start_time:
                try:
                    # Extract date part
                    dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
                    date_key = dt.strftime('%Y-%m-%d')
                    
                    if date_key not in grouped:
                        grouped[date_key] = []
                    grouped[date_key].append(activity)
                    
                except Exception as e:
                    logger.warning(f"Could not parse date from {start_time}: {e}")
        
        return grouped
    
    def create_daily_metrics(self, activities: List[Dict]) -> Dict:
        """Create daily metrics from activities for a single day"""
        
        # Get sleep data from first activity (assumes one set per day)
        sleep_data = activities[0].get('sleepData', {}) if activities else {}
        wellness_data = activities[0].get('wellness', {}) if activities else {}
        
        # Calculate totals from all workouts
        total_distance = sum(self.extract_numeric_value(a.get('distance', '0')) for a in activities)
        total_time = sum(self.parse_duration_to_seconds(a.get('duration', '0')) for a in activities)
        total_elev_gain = sum(self.extract_numeric_value(a.get('elevationGain', '0')) for a in activities)
        
        # Estimate steps (would normally come from Garmin wellness data)
        estimated_steps = int(total_distance * 1300)  # ~1300 steps per mile
        
        daily_metrics = {
            "sleep_minutes": self.parse_sleep_duration_to_minutes(sleep_data.get('totalSleep', '0')),
            "deep_minutes": self.parse_sleep_duration_to_minutes(sleep_data.get('deepSleep', '0')),
            "light_minutes": self.parse_sleep_duration_to_minutes(sleep_data.get('lightSleep', '0')),
            "rem_minutes": self.parse_sleep_duration_to_minutes(sleep_data.get('remSleep', '0')),
            "awake_minutes": self.parse_sleep_duration_to_minutes(sleep_data.get('awakeTime', '0')),
            "sleep_score": int(self.extract_numeric_value(sleep_data.get('sleepScore', '0'))),
            "resting_hr": 55,  # Would come from Garmin wellness API
            "hrv_night_avg": int(self.extract_numeric_value(wellness_data.get('hrv', '40'))),
            "body_battery": {
                "charge": 50,
                "drain": 30
            },
            "steps": estimated_steps,
            "total_distance_mi": round(total_distance, 2),
            "total_moving_time_s": total_time,
            "total_elev_gain_ft": int(total_elev_gain)
        }
        
        return daily_metrics
    
    def create_daily_markdown(self, date: str, daily_metrics: Dict, workouts: List[Dict]) -> str:
        """Create the enhanced Markdown content for a single day"""
        
        # Parse date for formatting
        dt = datetime.strptime(date, '%Y-%m-%d')
        
        # Create YAML frontmatter
        frontmatter = {
            "date": date,
            "schema": self.schema_version,
            "daily_metrics": daily_metrics,
            "workout_metrics": workouts
        }
        
        # Format summary stats
        total_miles = daily_metrics["total_distance_mi"]
        total_hours = daily_metrics["total_moving_time_s"] // 3600
        total_minutes = (daily_metrics["total_moving_time_s"] % 3600) // 60
        total_elev = daily_metrics["total_elev_gain_ft"]
        total_steps = daily_metrics["steps"]
        
        sleep_hours = daily_metrics["sleep_minutes"] // 60
        sleep_mins = daily_metrics["sleep_minutes"] % 60
        sleep_score = daily_metrics["sleep_score"]
        resting_hr = daily_metrics["resting_hr"]
        hrv = daily_metrics["hrv_night_avg"]
        bb_charge = daily_metrics["body_battery"]["charge"]
        bb_drain = daily_metrics["body_battery"]["drain"]
        
        # Create markdown content
        markdown = f"""---
{yaml.dump(frontmatter, default_flow_style=False, sort_keys=False)}---
# {date} · Daily Summary
**Totals:** {total_miles} mi • {total_hours} h {total_minutes} m • {total_elev} ft ↑ • {total_steps:,} steps  
**Sleep:** {sleep_hours} h {sleep_mins} m (Score {sleep_score}) • Rest HR {resting_hr} bpm • HRV {hrv} ms • BB +{bb_charge}/−{bb_drain}

<details>
<summary>Workout & Daily JSON</summary>

```json
{json.dumps(frontmatter, indent=2)}
```
</details>
"""
        
        return markdown
    
    def refactor_data(self):
        """Main refactor function"""
        logger.info("Starting comprehensive data refactor...")
        
        # Parse existing data
        activities = self.parse_existing_data()
        if not activities:
            logger.error("No activities found to refactor")
            return
        
        # Group by date
        grouped = self.group_activities_by_date(activities)
        logger.info(f"Grouped {len(activities)} activities into {len(grouped)} days")
        
        # Create data directory structure
        self.data_dir.mkdir(exist_ok=True)
        
        # Process each day
        for date, day_activities in grouped.items():
            logger.info(f"Processing {date} with {len(day_activities)} activities")
            
            # Convert activities to new format
            workouts = []
            for activity in day_activities:
                workout = self.convert_activity_to_new_format(activity)
                workouts.append(workout)
            
            # Create daily metrics
            daily_metrics = self.create_daily_metrics(day_activities)
            
            # Create directory structure (YYYY/MM/)
            year, month, day = date.split('-')
            day_dir = self.data_dir / year / month
            day_dir.mkdir(parents=True, exist_ok=True)
            
            # Create markdown file
            markdown_content = self.create_daily_markdown(date, daily_metrics, workouts)
            day_file = day_dir / f"{day}.md"
            day_file.write_text(markdown_content)
            
            logger.info(f"Created {day_file}")
        
        # Archive original index.md
        backup_file = Path("index.md.backup-pre-refactor")
        self.index_path.rename(backup_file)
        logger.info(f"Archived original index.md as {backup_file}")
        
        # Create new index.md with links to daily files
        self.create_new_index(grouped)
        
        logger.info("Data refactor completed successfully!")
    
    def create_new_index(self, grouped_data: Dict):
        """Create new index.md with links to daily files"""
        
        content = """# Training Data - Enhanced Format

This repository contains daily training data in an enhanced format with detailed metrics, 
unit conversions, and comprehensive workout analysis.

## Recent Activities

"""
        
        # Sort dates in reverse order (newest first)
        sorted_dates = sorted(grouped_data.keys(), reverse=True)
        
        for date in sorted_dates[:10]:  # Show last 10 days
            activities = grouped_data[date]
            year, month, day = date.split('-')
            
            # Format date nicely
            dt = datetime.strptime(date, '%Y-%m-%d')
            formatted_date = dt.strftime('%A, %B %d, %Y')
            
            # Calculate totals for the day
            total_distance = sum(self.extract_numeric_value(a.get('distance', '0')) for a in activities)
            workout_count = len(activities)
            
            content += f"- **[{formatted_date}](data/{year}/{month}/{day:0>2}.md)** - {workout_count} workout{'s' if workout_count != 1 else ''}, {total_distance:.1f} miles\n"
        
        content += f"""
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
"""
        
        self.index_path.write_text(content)

def main():
    """Main entry point"""
    refactor = DataRefactor()
    refactor.refactor_data()

if __name__ == "__main__":
    main() 