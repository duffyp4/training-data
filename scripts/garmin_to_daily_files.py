#!/usr/bin/env python3
"""
Garmin to Daily Files Converter
Converts activities.json from garmin_scraper to structured daily files in data/YYYY/MM/DD.md format
Uses the multipage design with YAML front matter, human-readable sections, and expandable JSON
Enhanced with FIT file data: training effects, HR zones, location, and per-split running dynamics
"""

import json
import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GarminToDailyFiles:
    def __init__(self):
        self.data_dir = Path("data")
        self.activities_path = Path("activities.json")
        self.last_id_file = self.data_dir / "last_id.json"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)

    def convert_old_activities_to_new_format(self, activities: List[Dict]) -> Dict[str, Dict]:
        """Convert activities.json format to new daily file structure"""
        daily_data = {}
        
        for activity in activities:
            # Extract date from activity
            date_str = self.extract_date_from_activity(activity)
            if not date_str:
                continue
                
            # Initialize daily data structure if needed
            if date_str not in daily_data:
                daily_data[date_str] = {
                    "date": date_str,
                    "schema": 2,
                    "sleep_metrics": {
                        "sleep_minutes": None,
                        "deep_minutes": None,
                        "light_minutes": None,
                        "rem_minutes": None,
                        "awake_minutes": None,
                        "sleep_score": None,
                        "hrv_night_avg": None
                    },
                    "daily_metrics": {
                        "body_battery": {
                            "charge": None,
                            "drain": None
                        },
                        "steps": None,
                        "resting_hr": None  # Moved from sleep_metrics
                    },
                    "workout_metrics": []
                    # Note: Removed self_evaluation section per user request
                }
            
            # Process sleep data if available
            if activity.get('sleepData'):
                sleep_data = activity['sleepData']
                daily_data[date_str]['sleep_metrics'].update({
                    "sleep_minutes": self.parse_duration_to_minutes(sleep_data.get('totalSleep')),
                    "deep_minutes": self.parse_duration_to_minutes(sleep_data.get('deepSleep')),
                    "light_minutes": self.parse_duration_to_minutes(sleep_data.get('lightSleep')),
                    "rem_minutes": self.parse_duration_to_minutes(sleep_data.get('remSleep')),
                    "awake_minutes": self.parse_duration_to_minutes(sleep_data.get('awakeTime')),
                    "sleep_score": sleep_data.get('sleepScore')
                })
            
            # Process wellness data if available
            if activity.get('wellness'):
                wellness = activity['wellness']
                daily_data[date_str]['daily_metrics'].update({
                    "steps": wellness.get('dailySteps'),
                    "resting_hr": wellness.get('restingHeartRate')
                })
                
                if wellness.get('bodyBattery'):
                    daily_data[date_str]['daily_metrics']['body_battery'] = wellness['bodyBattery']
                
                if wellness.get('hrv'):
                    daily_data[date_str]['sleep_metrics']['hrv_night_avg'] = wellness['hrv']
                
                # Add lactate threshold (NEW)
                if wellness.get('lactateThreshold'):
                    daily_data[date_str]['daily_metrics']['lactate_threshold'] = wellness['lactateThreshold']
            
            # Process workout data
            workout_data = self.convert_activity_to_workout_metrics(activity)
            if workout_data:
                daily_data[date_str]['workout_metrics'].append(workout_data)
        
        return daily_data

    def extract_date_from_activity(self, activity: Dict) -> Optional[str]:
        """Extract date in YYYY-MM-DD format from activity"""
        try:
            # Try startTime first (ISO format)
            if activity.get('startTime'):
                dt = datetime.fromisoformat(activity['startTime'].replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d')
            
            # Fallback to date field parsing
            if activity.get('date'):
                date_str = activity['date']
                if ',' in date_str:
                    date_part = date_str.split(',')[1].strip()
                    dt = datetime.strptime(date_part, "%m/%d/%Y")
                    return dt.strftime('%Y-%m-%d')
                    
        except Exception as e:
            logger.warning(f"Could not parse date from activity: {e}")
        
        return None

    def parse_duration_to_minutes(self, duration_str: Optional[str]) -> Optional[int]:
        """Convert duration string like '7h 30m' to minutes"""
        if not duration_str:
            return None
        
        try:
            total_minutes = 0
            # Parse hours
            if 'h' in duration_str:
                hours = int(duration_str.split('h')[0])
                total_minutes += hours * 60
            
            # Parse minutes
            if 'm' in duration_str:
                minutes_part = duration_str.split('h')[-1] if 'h' in duration_str else duration_str
                minutes = int(minutes_part.split('m')[0].strip())
                total_minutes += minutes
            
            return total_minutes if total_minutes > 0 else None
        except Exception:
            return None

    def convert_activity_to_workout_metrics(self, activity: Dict) -> Optional[Dict]:
        """Convert activity to workout_metrics format with enhanced FIT data"""
        try:
            # Parse distance
            distance_str = activity.get('distance', '')
            distance_mi = 0
            if distance_str and 'mi' in distance_str:
                distance_mi = float(distance_str.replace('mi', '').strip())
            
            # Parse duration to seconds
            duration_str = activity.get('duration', '')
            moving_time_s = self.parse_duration_to_seconds(duration_str)
            
            # Parse elevation
            elevation_str = activity.get('elevation', '')
            elev_gain_ft = 0
            if elevation_str and 'ft' in elevation_str:
                elev_gain_ft = int(elevation_str.replace('ft', '').strip())
            
            # Parse heart rate
            avg_hr = None
            max_hr = None
            avg_hr_str = activity.get('averageHeartRate', '')
            if 'bpm' in avg_hr_str:
                avg_hr = int(avg_hr_str.replace('bpm', '').strip())
            
            max_hr_str = activity.get('maxHeartRate', '')
            if 'bpm' in max_hr_str:
                max_hr = int(max_hr_str.replace('bpm', '').strip())
            
            # Parse pace to seconds per mile
            pace_str = activity.get('pace', '')
            avg_pace_s_per_mi = self.parse_pace_to_seconds(pace_str)
            
            workout = {
                "id": int(activity.get('activityId', 0)),
                "type": activity.get('sport', 'Unknown'),
                "start": activity.get('startTime'),
                "distance_mi": distance_mi,
                "moving_time_s": moving_time_s,
                "elev_gain_ft": elev_gain_ft,
                "avg_hr": avg_hr,
                "max_hr": max_hr,
                "avg_pace_s_per_mi": avg_pace_s_per_mi,
                "splits": self.convert_laps_to_splits(activity.get('laps', []))
            }
            
            # Add enhanced data from API responses
            if activity.get('location'):
                if isinstance(activity['location'], dict) and activity['location'].get('city'):
                    workout["location"] = activity['location']['city']
                else:
                    workout["location"] = activity['location']
            
            # Add Visual Crossing weather data
            if activity.get('weather'):
                workout["weather"] = activity['weather']
            
            # Add training effects from API
            if activity.get('training_effects'):
                workout["training_effects"] = activity['training_effects']
            
            # Add running dynamics from API
            if activity.get('running_dynamics'):
                workout["running_dynamics"] = activity['running_dynamics']
            
            # Add HR zones from API (NEW - replaces power zones)
            if activity.get('hr_zones'):
                workout["hr_zones"] = activity['hr_zones']
            elif activity.get('power_zones'):
                # Fallback to power zones if HR zones not available
                workout["power_zones"] = activity['power_zones']
            
            # Add power data from API
            if activity.get('power'):
                workout["power"] = activity['power']
            
            return workout
            
        except Exception as e:
            logger.warning(f"Could not convert activity to workout metrics: {e}")
            return None

    def parse_duration_to_seconds(self, duration_str: str) -> int:
        """Convert duration string like '35:49' or '1:02:08' to seconds"""
        if not duration_str:
            return 0
        
        try:
            parts = duration_str.split(':')
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
        except Exception:
            pass
        
        return 0

    def parse_pace_to_seconds(self, pace_str: str) -> Optional[int]:
        """Convert pace string like '10:49/mi' to seconds per mile"""
        if not pace_str or '/mi' not in pace_str:
            return None
        
        try:
            pace_part = pace_str.replace('/mi', '').strip()
            parts = pace_part.split(':')
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
        except Exception:
            pass
        
        return None

    def convert_laps_to_splits(self, laps: List[Dict]) -> List[Dict]:
        """Convert lap data to splits format with enhanced per-split running dynamics"""
        splits = []
        
        for i, lap in enumerate(laps):
            # Parse lap data
            distance_str = lap.get('distance', '')
            distance_mi = 0
            if 'mi' in distance_str:
                distance_mi = float(distance_str.replace('mi', '').strip())
            
            time_str = lap.get('time', '')
            mile_time_s = self.parse_duration_to_seconds(time_str)
            
            pace_str = lap.get('pace', '')
            avg_pace_s_per_mi = self.parse_pace_to_seconds(pace_str)
            
            elevation_str = lap.get('elevation', '')
            elev_gain_ft = 0
            if 'ft' in elevation_str:
                elev_gain_ft = int(elevation_str.replace('ft', '').strip())
            
            hr_str = lap.get('heartRate', '')
            avg_hr = None
            if 'bpm' in hr_str:
                avg_hr = int(hr_str.replace('bpm', '').strip())
            
            split = {
                "split": i + 1,  # CHANGED from "mile" to "split"
                "avg_hr": avg_hr,
                "max_hr": avg_hr,  # Will be enhanced from FIT data if available
                "avg_pace_s_per_mi": avg_pace_s_per_mi,
                "mile_time_s": mile_time_s,
                "elev_gain_ft": elev_gain_ft,
                "step_type": lap.get('stepType')  # From FIT data if available
            }
            
            # Add per-split running dynamics if available (from FIT file)
            if lap.get('runningDynamics'):
                split["running_dynamics"] = lap['runningDynamics']
            
            splits.append(split)
        
        return splits

    def generate_daily_file_content(self, daily_data: Dict) -> str:
        """Generate complete daily file content with multipage design"""
        
        # Generate YAML front matter
        yaml_content = yaml.dump(daily_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        # Generate human-readable summary
        summary_content = self.generate_summary_section(daily_data)
        
        # Generate structured readable sections
        structured_content = self.generate_structured_readable_sections(daily_data)
        
        # Generate expandable JSON section
        json_content = json.dumps(daily_data, indent=2)
        
        # Combine all sections
        full_content = f"""---
{yaml_content}---
{summary_content}

{structured_content}

<details>
<summary>Full JSON</summary>

```json
{json_content}
```
</details>
"""
        
        return full_content

    def generate_summary_section(self, daily_data: Dict) -> str:
        """Generate the daily summary section (REMOVED redundant totals)"""
        date = daily_data.get('date', '')
        
        # NO MORE TOTALS/SLEEP SUMMARY - just the title
        return f"# {date} · Daily Summary"

    def generate_structured_readable_sections(self, daily_data: Dict) -> str:
        """Generate human-readable structured sections"""
        content = []
        
        # Sleep Metrics Section
        content.append("## Sleep Metrics")
        sleep = daily_data.get('sleep_metrics', {})
        if any(v is not None for v in sleep.values()):
            if sleep.get('sleep_minutes'):
                hours = sleep['sleep_minutes'] // 60
                mins = sleep['sleep_minutes'] % 60
                content.append(f"**Total Sleep:** {hours}h {mins}m")
            
            # Sleep stages - EACH ON SEPARATE LINE (TRULY VERTICAL)
            if sleep.get('deep_minutes'):
                content.append(f"**Deep Sleep:** {sleep['deep_minutes']}m")
            if sleep.get('light_minutes'):
                content.append(f"**Light Sleep:** {sleep['light_minutes']}m")
            if sleep.get('rem_minutes'):
                content.append(f"**REM Sleep:** {sleep['rem_minutes']}m")
            if sleep.get('awake_minutes'):
                content.append(f"**Awake Time:** {sleep['awake_minutes']}m")
            
            if sleep.get('sleep_score'):
                content.append(f"**Sleep Score:** {sleep['sleep_score']}")
            
            if sleep.get('hrv_night_avg'):
                content.append(f"**HRV:** {sleep['hrv_night_avg']} ms")
        else:
            content.append("No sleep data available for this date")
        
        content.append("")  # Empty line
        
        # Daily Metrics Section (ALL VERTICAL)
        content.append("## Daily Metrics")
        daily = daily_data.get('daily_metrics', {})
        
        if daily.get('steps'):
            content.append(f"**Steps:** {daily['steps']:,}")
        
        # Body Battery (TRULY VERTICAL - separate lines for charge/drain)  
        bb = daily.get('body_battery', {})
        if bb.get('charge') is not None and bb.get('charge') > 0:
            content.append(f"**Body Battery Charge:** +{bb['charge']}")
        if bb.get('drain') is not None and bb.get('drain') > 0:
            content.append(f"**Body Battery Drain:** -{bb['drain']}")
        
        if daily.get('resting_hr'):
            content.append(f"**Resting Heart Rate:** {daily['resting_hr']} bpm")
        
        # Lactate Threshold (NEW)
        if daily.get('lactate_threshold'):
            lt = daily['lactate_threshold']
            lt_parts = []
            if lt.get('heart_rate_bpm'):
                lt_parts.append(f"{lt['heart_rate_bpm']} bpm")
            if lt.get('speed_mps'):
                lt_parts.append(f"{lt['speed_mps']} m/s")
            if lt_parts:
                content.append(f"**Lactate Threshold:** {' / '.join(lt_parts)}")
        
        # Check if we have any daily metrics to show
        if not any([daily.get('steps'), bb.get('charge'), bb.get('drain'), daily.get('resting_hr'), daily.get('lactate_threshold')]):
            content.append("No daily wellness data available for this date")
        
        content.append("")  # Empty line
        
        # Workout Details Section
        workouts = daily_data.get('workout_metrics', [])
        if workouts:
            content.append("## Workout Details")
            
            for i, workout in enumerate(workouts):
                if len(workouts) > 1:
                    content.append(f"### Workout {i+1}: {workout.get('type', 'Unknown')}")
                else:
                    content.append(f"### {workout.get('type', 'Unknown')}")
                
                # Basic workout info (VERTICAL)
                if workout.get('distance_mi'):
                    content.append(f"**Distance:** {workout['distance_mi']:.2f} mi")
                if workout.get('moving_time_s'):
                    time_str = self.format_time_duration(workout['moving_time_s'])
                    content.append(f"**Time:** {time_str}")
                if workout.get('elev_gain_ft'):
                    content.append(f"**Elevation Gain:** {workout['elev_gain_ft']} ft")
                
                # Location (from enhanced API data)
                if workout.get('location'):
                    content.append(f"**Location:** {workout['location']}")
                
                # Weather data (TRULY VERTICAL format - each metric on separate line)
                if workout.get('weather'):
                    weather = workout['weather']
                    
                    # Temperature on separate line
                    if weather.get('temperature'):
                        temp = weather['temperature']
                        content.append(f"**Temperature:** {temp.get('start', '?')}°F → {temp.get('end', '?')}°F")
                    
                    # Humidity on separate line
                    if weather.get('humidity'):
                        humidity = weather['humidity']
                        content.append(f"**Humidity:** {humidity.get('start', '?')}% → {humidity.get('end', '?')}%")
                    
                    # Dew Point on separate line
                    if weather.get('dew_point'):
                        dew = weather['dew_point']
                        content.append(f"**Dew Point:** {dew.get('start', '?')}°F → {dew.get('end', '?')}°F")
                    
                    # Conditions on separate line
                    if weather.get('conditions'):
                        content.append(f"**Conditions:** {weather['conditions']}")
                
                # Heart rate
                if workout.get('avg_hr') and workout.get('max_hr'):
                    content.append(f"**Heart Rate:** Avg: {workout['avg_hr']} bpm, Max: {workout['max_hr']} bpm")
                elif workout.get('avg_hr'):
                    content.append(f"**Heart Rate:** Avg: {workout['avg_hr']} bpm")
                
                # Pace
                if workout.get('avg_pace_s_per_mi'):
                    pace_str = self.format_pace(workout['avg_pace_s_per_mi'])
                    content.append(f"**Average Pace:** {pace_str}")
                
                # Training Effects (TRULY VERTICAL - each effect on separate line)
                if workout.get('training_effects'):
                    effects = workout['training_effects']
                    if effects.get('aerobic'):
                        content.append(f"**Aerobic Training Effect:** {effects['aerobic']}")
                    if effects.get('anaerobic'):
                        content.append(f"**Anaerobic Training Effect:** {effects['anaerobic']}")
                    if effects.get('label'):
                        content.append(f"**Training Effect Label:** {effects['label']}")
                    if effects.get('training_load'):
                        content.append(f"**Training Load:** {effects['training_load']}")
                
                # Running Dynamics (TRULY VERTICAL - each metric on separate line)
                if workout.get('running_dynamics'):
                    dynamics = workout['running_dynamics']
                    if dynamics.get('cadence_spm'):
                        content.append(f"**Cadence:** {dynamics['cadence_spm']} spm")
                    if dynamics.get('stride_length_cm'):
                        content.append(f"**Stride Length:** {dynamics['stride_length_cm']} cm")
                    if dynamics.get('ground_contact_time_ms'):
                        content.append(f"**Ground Contact Time:** {dynamics['ground_contact_time_ms']} ms")
                    if dynamics.get('vertical_oscillation_mm'):
                        content.append(f"**Vertical Oscillation:** {dynamics['vertical_oscillation_mm']} mm")
                    if dynamics.get('vertical_ratio_percent'):
                        content.append(f"**Vertical Ratio:** {dynamics['vertical_ratio_percent']}%")
                
                # Power Data (TRULY VERTICAL - each metric on separate line)
                if workout.get('power'):
                    power = workout['power']
                    if power.get('average'):
                        content.append(f"**Average Power:** {power['average']}W")
                    if power.get('maximum'):
                        content.append(f"**Maximum Power:** {power['maximum']}W")
                    if power.get('normalized'):
                        content.append(f"**Normalized Power:** {power['normalized']}W")
                
                # HR Zones (NEW - replaces Power Zones)
                if workout.get('hr_zones'):
                    zones_parts = []
                    for zone, time in workout['hr_zones'].items():
                        if time != "0:00":  # Only show zones with time
                            zone_num = zone.replace('zone_', '').upper()
                            zones_parts.append(f"Z{zone_num}: {time}")
                    if zones_parts:
                        content.append(f"**HR Zones:** {' • '.join(zones_parts)}")
                elif workout.get('power_zones'):
                    # Fallback to power zones if HR zones not available
                    zones_parts = []
                    for zone, time in workout['power_zones'].items():
                        if time != "0:00":  # Only show zones with time
                            zone_num = zone.replace('zone_', '').upper()
                            zones_parts.append(f"Z{zone_num}: {time}")
                    if zones_parts:
                        content.append(f"**Power Zones:** {' • '.join(zones_parts)}")
                
                # Splits TABLE FORMAT (NEW with styling)
                splits = workout.get('splits', [])
                if splits:
                    content.append("")
                    content.append("## Splits")
                    content.append("")
                    
                    # Add CSS styling for better table appearance
                    content.append('<style>')
                    content.append('table { border-collapse: collapse; width: 100%; margin: 16px 0; }')
                    content.append('th { background-color: #2d3748; color: white; padding: 12px 8px; text-align: center; font-weight: bold; }')
                    content.append('td { padding: 8px; text-align: center; border: 1px solid #e2e8f0; }')
                    content.append('tr:nth-child(even) { background-color: #f7fafc; }')
                    content.append('tr:nth-child(odd) { background-color: #ffffff; }')
                    content.append('tr:hover { background-color: #edf2f7; }')
                    content.append('</style>')
                    content.append("")
                    
                    # Table header
                    content.append("| Split | Time | Pace | HR Avg | HR Max | Elev | Cadence | Stride | GCT | VO |")
                    content.append("|-------|------|------|---------|---------|------|---------|--------|-----|-----|")
                    
                    # Table rows
                    for split in splits:
                        split_num = split.get('split', split.get('mile', '?'))  # Handle both old "mile" and new "split"
                        
                        # Time
                        time_s = split.get('mile_time_s', 0)
                        time_str = self.format_time_duration(time_s) if time_s > 0 else "N/A"
                        
                        # Pace
                        pace_str = self.format_pace(split.get('avg_pace_s_per_mi')) if split.get('avg_pace_s_per_mi') else "N/A"
                        
                        # Heart rate
                        hr_avg = split.get('avg_hr', '') or 'N/A'
                        hr_max = split.get('max_hr', '') or 'N/A'
                        
                        # Elevation
                        elev = split.get('elev_gain_ft', 0)
                        elev_str = f"{elev:+d} ft" if elev != 0 else "0 ft"
                        
                        # Running dynamics
                        cadence = stride = gct = vo = "N/A"
                        if split.get('running_dynamics'):
                            rd = split['running_dynamics']
                            cadence = f"{rd.get('cadence_spm', 'N/A')} spm" if rd.get('cadence_spm') else "N/A"
                            stride = f"{rd.get('stride_length_cm', 'N/A')} cm" if rd.get('stride_length_cm') else "N/A"
                            gct = f"{rd.get('ground_contact_time_ms', 'N/A')} ms" if rd.get('ground_contact_time_ms') else "N/A"
                            vo = f"{rd.get('vertical_oscillation_mm', 'N/A')} mm" if rd.get('vertical_oscillation_mm') else "N/A"
                        
                        content.append(f"| {split_num} | {time_str} | {pace_str} | {hr_avg} | {hr_max} | {elev_str} | {cadence} | {stride} | {gct} | {vo} |")
                
                content.append("")  # Empty line between workouts
        
        return '\n'.join(content)

    def format_time_duration(self, seconds: int) -> str:
        """Format seconds to human readable duration"""
        if seconds <= 0:
            return "0s"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours} h {minutes} m"
        elif minutes > 0:
            return f"{minutes} m {secs} s"
        else:
            return f"{secs}s"

    def format_pace(self, seconds_per_mile: int) -> str:
        """Format pace in seconds per mile to MM:SS/mi"""
        if not seconds_per_mile or seconds_per_mile <= 0:
            return "N/A"
        
        minutes = seconds_per_mile // 60
        seconds = seconds_per_mile % 60
        return f"{minutes}:{seconds:02d}/mi"

    def write_daily_file(self, date_str: str, daily_data: Dict):
        """Write daily data to file"""
        # Parse date to create directory structure
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        year_dir = self.data_dir / str(dt.year)
        month_dir = year_dir / f"{dt.month:02d}"
        
        # Create directories
        month_dir.mkdir(parents=True, exist_ok=True)
        
        # Write file
        file_path = month_dir / f"{dt.day:02d}.md"
        content = self.generate_daily_file_content(daily_data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created daily file: {file_path}")

    def update_last_id(self, activities: List[Dict]):
        """Update last_id.json with the newest activity"""
        if not activities:
            return
        
        # Find the newest activity by ID
        newest_activity = max(activities, key=lambda x: int(x.get('activityId', '0')))
        
        last_data = {
            "last_id": newest_activity.get('activityId'),
            "last_date": self.extract_date_from_activity(newest_activity)
        }
        
        with open(self.last_id_file, 'w') as f:
            json.dump(last_data, f, indent=2)
        
        logger.info(f"Updated last_id.json to: ID={last_data['last_id']}, Date={last_data['last_date']}")

    def process_activities(self):
        """Main processing function"""
        logger.info("Starting Garmin to daily files conversion...")
        
        # Read activities from scraper output
        try:
            with open(self.activities_path, 'r') as f:
                activities = json.load(f)
        except FileNotFoundError:
            logger.error("activities.json not found. Run the Garmin scraper first.")
            return
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in activities.json: {e}")
            return
        
        if not activities:
            logger.info("No activities to process.")
            return
        
        logger.info(f"Processing {len(activities)} activities")
        
        # Convert to daily data structure
        daily_data = self.convert_old_activities_to_new_format(activities)
        
        # Write daily files
        for date_str, data in daily_data.items():
            self.write_daily_file(date_str, data)
        
        # Update last_id tracking
        self.update_last_id(activities)
        
        logger.info(f"Successfully created {len(daily_data)} daily files")

def main():
    """Main entry point"""
    try:
        converter = GarminToDailyFiles()
        converter.process_activities()
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        exit(1)

if __name__ == "__main__":
    main() 