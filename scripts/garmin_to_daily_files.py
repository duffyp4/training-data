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
            
            # Add power zones from API
            if activity.get('power_zones'):
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
                "mile": i + 1,
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
        """Generate the daily summary section"""
        date = daily_data.get('date', '')
        
        # Calculate totals from workouts
        total_distance = 0
        total_time = 0
        total_elevation = 0
        workout_count = len(daily_data.get('workout_metrics', []))
        
        for workout in daily_data.get('workout_metrics', []):
            total_distance += workout.get('distance_mi', 0)
            total_time += workout.get('moving_time_s', 0)
            total_elevation += workout.get('elev_gain_ft', 0)
        
        # Format time
        time_str = self.format_time_duration(total_time)
        
        # Format distance
        distance_str = f"{total_distance:.1f} mi" if total_distance > 0 else "0 mi"
        
        # Steps
        steps = daily_data.get('daily_metrics', {}).get('steps')
        steps_str = f"{steps:,} steps" if steps else "0 steps"
        
        # Sleep summary
        sleep_minutes = daily_data.get('sleep_metrics', {}).get('sleep_minutes')
        if sleep_minutes:
            hours = sleep_minutes // 60
            mins = sleep_minutes % 60
            sleep_str = f"{hours}h {mins}m sleep"
        else:
            sleep_str = "No sleep data available for this date"
        
        workout_text = "workout" if workout_count == 1 else "workouts"
        
        return f"""# {date} · Daily Summary
**Totals:** {distance_str} • {time_str} • {total_elevation} ft ↑ • {steps_str}  
**Sleep:** {sleep_str}"""

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
            
            if any([sleep.get('deep_minutes'), sleep.get('light_minutes'), sleep.get('rem_minutes')]):
                stages = []
                if sleep.get('deep_minutes'):
                    stages.append(f"Deep: {sleep['deep_minutes']}m")
                if sleep.get('light_minutes'):
                    stages.append(f"Light: {sleep['light_minutes']}m")
                if sleep.get('rem_minutes'):
                    stages.append(f"REM: {sleep['rem_minutes']}m")
                if sleep.get('awake_minutes'):
                    stages.append(f"Awake: {sleep['awake_minutes']}m")
                content.append(f"**Sleep Stages:** {' • '.join(stages)}")
            
            if sleep.get('sleep_score'):
                content.append(f"**Sleep Score:** {sleep['sleep_score']}")
            
            if sleep.get('hrv_night_avg'):
                content.append(f"**HRV:** {sleep['hrv_night_avg']} ms")
        else:
            content.append("No sleep data available for this date")
        
        content.append("")  # Empty line
        
        # Daily Metrics Section
        content.append("## Daily Metrics")
        daily = daily_data.get('daily_metrics', {})
        
        if daily.get('steps'):
            content.append(f"**Steps:** {daily['steps']:,}")
        
        # Body Battery 
        bb = daily.get('body_battery', {})
        if bb.get('charge') is not None or bb.get('drain') is not None:
            bb_info = []
            if bb.get('charge'):
                bb_info.append(f"Charged: +{bb['charge']}")
            if bb.get('drain'):
                bb_info.append(f"Drained: -{bb['drain']}")
            content.append(f"**Body Battery:** {' • '.join(bb_info)}")
        
        if daily.get('resting_hr'):
            content.append(f"**Resting Heart Rate:** {daily['resting_hr']} bpm")
        
        # Check if we have any daily metrics to show
        if not any([daily.get('steps'), bb.get('charge'), bb.get('drain'), daily.get('resting_hr')]):
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
                
                # Basic workout info
                workout_info = []
                if workout.get('distance_mi'):
                    workout_info.append(f"{workout['distance_mi']:.2f} mi")
                if workout.get('moving_time_s'):
                    workout_info.append(self.format_time_duration(workout['moving_time_s']))
                if workout.get('elev_gain_ft'):
                    workout_info.append(f"{workout['elev_gain_ft']} ft ↑")
                
                if workout_info:
                    content.append(f"**Distance & Time:** {' • '.join(workout_info)}")
                
                # Location (from enhanced API data)
                if workout.get('location'):
                    content.append(f"**Location:** {workout['location']}")
                
                # Weather data (Visual Crossing API format)
                if workout.get('weather'):
                    weather = workout['weather']
                    weather_info = []
                    
                    # Temperature: "start_temp -> finish_temp"
                    if weather.get('temperature'):
                        temp = weather['temperature']
                        temp_str = f"{temp.get('start', '?')}°F → {temp.get('end', '?')}°F"
                        weather_info.append(temp_str)
                    
                    # Humidity: "start_humidity -> finish_humidity"
                    if weather.get('humidity'):
                        humidity = weather['humidity']
                        humidity_str = f"{humidity.get('start', '?')}% → {humidity.get('end', '?')}% humidity"
                        weather_info.append(humidity_str)
                    
                    # Dew Point: "start_dew -> finish_dew"
                    if weather.get('dew_point'):
                        dew = weather['dew_point']
                        dew_str = f"{dew.get('start', '?')}°F → {dew.get('end', '?')}°F dew point"
                        weather_info.append(dew_str)
                    
                    # Conditions
                    if weather.get('conditions'):
                        weather_info.append(weather['conditions'])
                    
                    if weather_info:
                        content.append(f"**Weather:** {' • '.join(weather_info)}")
                
                # Heart rate
                if workout.get('avg_hr') and workout.get('max_hr'):
                    content.append(f"**Heart Rate:** Avg: {workout['avg_hr']} bpm, Max: {workout['max_hr']} bpm")
                elif workout.get('avg_hr'):
                    content.append(f"**Heart Rate:** Avg: {workout['avg_hr']} bpm")
                
                # Pace
                if workout.get('avg_pace_s_per_mi'):
                    pace_str = self.format_pace(workout['avg_pace_s_per_mi'])
                    content.append(f"**Average Pace:** {pace_str}")
                
                # Training Effects (from enhanced API data)
                if workout.get('training_effects'):
                    effects = workout['training_effects']
                    effects_info = []
                    if effects.get('aerobic'):
                        effects_info.append(f"Aerobic: {effects['aerobic']}")
                    if effects.get('anaerobic'):
                        effects_info.append(f"Anaerobic: {effects['anaerobic']}")
                    if effects.get('label'):
                        effects_info.append(f"({effects['label']})")
                    if effects_info:
                        content.append(f"**Training Effects:** {' • '.join(effects_info)}")
                
                # Running Dynamics (workout averages from API)
                if workout.get('running_dynamics'):
                    dynamics = workout['running_dynamics']
                    dynamics_info = []
                    if dynamics.get('cadence_spm'):
                        dynamics_info.append(f"Cadence: {dynamics['cadence_spm']} spm")
                    if dynamics.get('stride_length_cm'):
                        dynamics_info.append(f"Stride: {dynamics['stride_length_cm']} cm")
                    if dynamics.get('ground_contact_time_ms'):
                        dynamics_info.append(f"GCT: {dynamics['ground_contact_time_ms']} ms")
                    if dynamics.get('vertical_oscillation_mm'):
                        dynamics_info.append(f"VO: {dynamics['vertical_oscillation_mm']} mm")
                    if dynamics_info:
                        content.append(f"**Running Dynamics:** {' • '.join(dynamics_info)}")
                
                # Power Data (from API)
                if workout.get('power'):
                    power = workout['power']
                    power_info = []
                    if power.get('average'):
                        power_info.append(f"Avg: {power['average']}W")
                    if power.get('maximum'):
                        power_info.append(f"Max: {power['maximum']}W")
                    if power.get('normalized'):
                        power_info.append(f"NP: {power['normalized']}W")
                    if power_info:
                        content.append(f"**Power:** {' • '.join(power_info)}")
                
                # Power Zones (from API - can be used to show pattern for HR zones)
                if workout.get('power_zones'):
                    zones_info = []
                    for zone, time in workout['power_zones'].items():
                        if time != "0:00":  # Only show zones with time
                            zone_num = zone.replace('zone_', '').upper()
                            zones_info.append(f"Z{zone_num}: {time}")
                    if zones_info:
                        content.append(f"**Power Zones:** {' • '.join(zones_info)}")
                
                # Splits with enhanced running dynamics
                splits = workout.get('splits', [])
                if splits:
                    content.append("")
                    content.append("**Splits:**")
                    content.append("")
                    
                    for split in splits:
                        mile = split.get('mile', '?')
                        
                        # Time formatting
                        time_s = split.get('mile_time_s', 0)
                        time_str = self.format_time_duration(time_s) if time_s > 0 else "N/A"
                        
                        # Pace formatting
                        pace_str = self.format_pace(split.get('avg_pace_s_per_mi')) if split.get('avg_pace_s_per_mi') else "N/A"
                        
                        # Heart rate
                        hr_str = f"Avg: {split.get('avg_hr')} bpm" if split.get('avg_hr') else "N/A"
                        if split.get('max_hr') and split.get('max_hr') != split.get('avg_hr'):
                            hr_str += f", Max: {split['max_hr']} bpm"
                        
                        # Elevation
                        elev = split.get('elev_gain_ft', 0)
                        elev_str = f"{elev:+d} ft" if elev != 0 else "0 ft"
                        
                        content.append(f"**Mile {mile}:** {time_str} • {pace_str} • {hr_str} • {elev_str}")
                        
                        # Running dynamics (per-split from enhanced API data)
                        if split.get('running_dynamics'):
                            dynamics = split['running_dynamics']
                            dynamics_info = []
                            if dynamics.get('cadence_spm'):
                                dynamics_info.append(f"Cadence: {dynamics['cadence_spm']} spm")
                            if dynamics.get('stride_length_cm'):
                                dynamics_info.append(f"Stride: {dynamics['stride_length_cm']} cm")
                            if dynamics.get('ground_contact_time_ms'):
                                dynamics_info.append(f"GCT: {dynamics['ground_contact_time_ms']} ms")
                            if dynamics.get('vertical_oscillation_mm'):
                                dynamics_info.append(f"VO: {dynamics['vertical_oscillation_mm']} mm")
                            if dynamics.get('vertical_ratio_percent'):
                                dynamics_info.append(f"VR: {dynamics['vertical_ratio_percent']}%")
                            
                            if dynamics_info:
                                content.append(f"  *Running Dynamics:* {' • '.join(dynamics_info)}")
                        
                        # Power data (per-split from enhanced API data)
                        if split.get('power'):
                            power = split['power']
                            power_info = []
                            if power.get('average'):
                                power_info.append(f"Avg: {power['average']}W")
                            if power.get('maximum'):
                                power_info.append(f"Max: {power['maximum']}W")
                            if power.get('normalized'):
                                power_info.append(f"NP: {power['normalized']}W")
                            
                            if power_info:
                                content.append(f"  *Power:* {' • '.join(power_info)}")
                        
                        content.append("")
                
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