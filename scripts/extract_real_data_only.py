#!/usr/bin/env python3
"""
Real Data Only Extraction
Extract ONLY authentic data from original sources.
NO defaults, NO fabrication, NO made-up wellness data.
"""

import json
import re
import yaml
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RealDataExtractor:
    def __init__(self):
        self.backup_file = Path("index.md.backup-pre-refactor")
        self.data_dir = Path("data")
        
    def parse_original_strava_data(self):
        """Parse ONLY real data from original Strava backup"""
        if not self.backup_file.exists():
            logger.error("Original backup file not found")
            return []
        
        content = self.backup_file.read_text()
        
        # Find all JSON-LD blocks
        pattern = r'```jsonld\n(.*?)\n```'
        matches = re.findall(pattern, content, re.DOTALL)
        
        real_activities = []
        for match in matches:
            try:
                activity = json.loads(match)
                real_activities.append(activity)
            except json.JSONDecodeError as e:
                logger.warning(f"Could not parse JSON: {e}")
                continue
        
        logger.info(f"Found {len(real_activities)} real activities")
        return real_activities
    
    def convert_to_clean_format(self, activity):
        """Convert real Strava data to clean format with NO fabrication"""
        
        # Extract real basic data only
        workout = {
            "id": int(activity.get("identifier", "0")),
            "type": activity.get("exerciseType", "Run"),
            "start": activity.get("startTime", ""),
            "distance_mi": self.parse_distance(activity.get("distance", "0 mi")),
            "moving_time_s": self.parse_duration(activity.get("duration", "0:00")),
            "elev_gain_ft": self.parse_elevation(activity.get("elevationGain", "0 ft")),
            "avg_hr": self.parse_heart_rate(activity.get("averageHeartRate", "")),
            "avg_pace_s_per_mi": self.parse_pace(activity.get("pace", "")),
            "calories": int(activity.get("calories", "0"))
        }
        
        # Add real weather if available
        weather = activity.get("weather", {})
        if weather:
            workout["weather"] = {
                "temperature_f": self.parse_temperature(weather.get("temperature", "")),
                "humidity_pct": self.parse_percentage(weather.get("humidity", "")),
                "description": weather.get("description", "")
            }
        
        # Extract real lap data only
        laps = activity.get("laps", [])
        if laps:
            splits = []
            for i, lap in enumerate(laps):
                split = {
                    "mile": i + 1,
                    "distance_mi": self.parse_distance(lap.get("distance", "0 mi")),
                    "time_s": self.parse_duration(lap.get("time", "0:00")),
                    "pace_s_per_mi": self.parse_pace(lap.get("pace", "")),
                    "elev_gain_ft": self.parse_elevation(lap.get("elevation", "0 ft")),
                    "hr_bpm": self.parse_heart_rate(lap.get("heartRate", ""))
                }
                # Only include fields that have real values
                splits.append({k: v for k, v in split.items() if v is not None and v != 0})
            
            workout["splits"] = splits
        
        # Remove empty/null values
        return {k: v for k, v in workout.items() if v is not None and v != 0 and v != ""}
    
    def parse_distance(self, distance_str):
        """Extract distance in miles"""
        if not distance_str:
            return None
        match = re.search(r'([\d.]+)', str(distance_str))
        return round(float(match.group(1)), 2) if match else None
    
    def parse_duration(self, duration_str):
        """Convert duration to seconds"""
        if not duration_str:
            return None
        
        # Handle formats like "1:22:41" or "35:49"
        parts = str(duration_str).split(':')
        try:
            if len(parts) == 2:  # MM:SS
                return int(parts[0]) * 60 + int(parts[1])
            elif len(parts) == 3:  # HH:MM:SS
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        except ValueError:
            pass
        return None
    
    def parse_elevation(self, elev_str):
        """Extract elevation in feet"""
        if not elev_str:
            return None
        match = re.search(r'(-?[\d.]+)', str(elev_str))
        return int(float(match.group(1))) if match else None
    
    def parse_heart_rate(self, hr_str):
        """Extract heart rate in BPM"""
        if not hr_str:
            return None
        match = re.search(r'(\d+)', str(hr_str))
        return int(match.group(1)) if match else None
    
    def parse_pace(self, pace_str):
        """Convert pace to seconds per mile"""
        if not pace_str or "mi" not in str(pace_str):
            return None
        
        # Extract "11:48" from "11:48 /mi"
        pace_part = str(pace_str).split('/')[0].strip()
        parts = pace_part.split(':')
        try:
            if len(parts) == 2:
                return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            pass
        return None
    
    def parse_temperature(self, temp_str):
        """Extract temperature in Fahrenheit"""
        if not temp_str:
            return None
        match = re.search(r'(\d+)', str(temp_str))
        return int(match.group(1)) if match else None
    
    def parse_percentage(self, pct_str):
        """Extract percentage"""
        if not pct_str:
            return None
        match = re.search(r'(\d+)', str(pct_str))
        return int(match.group(1)) if match else None
    
    def group_by_date(self, activities):
        """Group activities by date"""
        grouped = {}
        for activity in activities:
            start_time = activity.get("start", "")
            if start_time:
                try:
                    # Extract date from ISO timestamp
                    date = start_time[:10]  # YYYY-MM-DD
                    if date not in grouped:
                        grouped[date] = []
                    grouped[date].append(activity)
                except:
                    logger.warning(f"Could not parse date from {start_time}")
        return grouped
    
    def create_daily_file(self, date, activities):
        """Create a clean daily file with ONLY real data"""
        
        # Calculate real totals from actual data
        total_distance = sum(a.get("distance_mi", 0) for a in activities)
        total_time = sum(a.get("moving_time_s", 0) for a in activities)
        total_elevation = sum(a.get("elev_gain_ft", 0) for a in activities)
        total_calories = sum(a.get("calories", 0) for a in activities)
        
        # Create YAML front-matter with ONLY real data
        frontmatter = {
            "date": date,
            "schema": 3,  # New schema for real-data-only
            "summary": {
                "workouts": len(activities),
                "total_distance_mi": round(total_distance, 2),
                "total_time_s": total_time,
                "total_elevation_ft": total_elevation,
                "total_calories": total_calories
            },
            "workouts": activities
        }
        
        # Remove any empty/null values
        def clean_dict(d):
            if isinstance(d, dict):
                return {k: clean_dict(v) for k, v in d.items() if v is not None and v != "" and v != 0}
            elif isinstance(d, list):
                return [clean_dict(item) for item in d if item is not None]
            return d
        
        clean_frontmatter = clean_dict(frontmatter)
        
        # Generate markdown
        yaml_str = yaml.dump(clean_frontmatter, default_flow_style=False, sort_keys=False)
        
        hours = total_time // 3600
        minutes = (total_time % 3600) // 60
        
        markdown = f"""---
{yaml_str}---
# {date} · Training Data (Real Data Only)
**{len(activities)} workout{'s' if len(activities) != 1 else ''} • {total_distance:.1f} mi • {hours}h {minutes}m • {total_elevation} ft ↑ • {total_calories} cal**

*This file contains only authentic data from actual workouts. No fabricated wellness or running dynamics.*

<details>
<summary>Full Data</summary>

```json
{json.dumps(clean_frontmatter, indent=2)}
```
</details>
"""
        return markdown
    
    def extract_all_real_data(self):
        """Extract all real data and create clean daily files"""
        logger.info("Extracting REAL DATA ONLY...")
        
        # Parse original Strava data
        activities = self.parse_original_strava_data()
        if not activities:
            logger.error("No real activities found")
            return
        
        # Convert to clean format
        clean_activities = []
        for activity in activities:
            clean_activity = self.convert_to_clean_format(activity)
            if clean_activity:
                clean_activities.append(clean_activity)
        
        logger.info(f"Converted {len(clean_activities)} activities to clean format")
        
        # Group by date
        grouped = self.group_by_date(clean_activities)
        logger.info(f"Grouped into {len(grouped)} days")
        
        # Remove existing fabricated data
        if self.data_dir.exists():
            import shutil
            shutil.rmtree(self.data_dir)
            logger.info("Removed fabricated data directory")
        
        # Create clean data structure
        self.data_dir.mkdir(exist_ok=True)
        
        for date, day_activities in grouped.items():
            year, month, day = date.split('-')
            day_dir = self.data_dir / year / month
            day_dir.mkdir(parents=True, exist_ok=True)
            
            # Create clean daily file
            markdown = self.create_daily_file(date, day_activities)
            day_file = day_dir / f"{day}.md"
            day_file.write_text(markdown)
            
            logger.info(f"Created real-data-only file: {day_file}")
        
        # Create index
        self.create_index(grouped)
        
        logger.info("✅ Real data extraction complete - NO FABRICATED DATA!")
    
    def create_index(self, grouped_data):
        """Create index with real data only"""
        index_data = []
        for date in sorted(grouped_data.keys(), reverse=True):
            activities = grouped_data[date]
            year, month, day = date.split('-')
            index_data.append({
                "date": date,
                "path": f"data/{year}/{month}/{day}.md",
                "workouts": len(activities),
                "distance_mi": round(sum(a.get("distance_mi", 0) for a in activities), 2)
            })
        
        index_path = self.data_dir / "index.json"
        with open(index_path, 'w') as f:
            json.dump(index_data, f, indent=2)
        
        logger.info(f"Created real-data index: {index_path}")

def main():
    extractor = RealDataExtractor()
    extractor.extract_all_real_data()

if __name__ == "__main__":
    main() 