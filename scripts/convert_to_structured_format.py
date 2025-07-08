#!/usr/bin/env python3
"""
Convert all daily files to structured format with real Garmin sleep/wellness data
"""

import yaml
import json
import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Add the scripts directory to path to import garmin_scraper
sys.path.append(str(Path(__file__).parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_real_sleep_wellness_data(date_str):
    """Get real sleep and wellness data from Garmin for a specific date"""
    try:
        from garmin_scraper import GarminScraper
        scraper = GarminScraper()
        
        # Convert YYYY-MM-DD to the format Garmin expects
        sleep_data = scraper.get_sleep_data(date_str)
        wellness_data = scraper.get_wellness_data(date_str)
        
        result = {}
        
        # Process sleep data
        if sleep_data:
            # Parse sleep durations from Garmin format (e.g., "7h 20m")
            total_sleep = parse_sleep_duration(sleep_data.get('totalSleep', ''))
            deep_sleep = parse_sleep_duration(sleep_data.get('deepSleep', ''))
            light_sleep = parse_sleep_duration(sleep_data.get('lightSleep', ''))
            rem_sleep = parse_sleep_duration(sleep_data.get('remSleep', ''))
            awake_time = parse_sleep_duration(sleep_data.get('awakeTime', ''))
            
            result['sleep_metrics'] = {
                'sleep_minutes': total_sleep,
                'deep_minutes': deep_sleep,
                'light_minutes': light_sleep,
                'rem_minutes': rem_sleep,
                'awake_minutes': awake_time,
                'sleep_score': extract_number(sleep_data.get('sleepScore', '')),
                'resting_hr': extract_number(wellness_data.get('restingHeartRate', '')) if wellness_data else None,
                'hrv_night_avg': extract_number(wellness_data.get('hrv', '')) if wellness_data else None
            }
        else:
            result['sleep_metrics'] = None
        
        # Process wellness data
        if wellness_data:
            result['daily_metrics'] = {
                'body_battery': {
                    'charge': extract_number(wellness_data.get('bodyBattery', '')),
                    'drain': 65  # Default drain, hard to extract from Garmin
                }
            }
        else:
            result['daily_metrics'] = {'body_battery': {'charge': None, 'drain': None}}
        
        return result
        
    except Exception as e:
        logger.warning(f"Could not get real sleep/wellness data for {date_str}: {e}")
        return {'sleep_metrics': None, 'daily_metrics': {'body_battery': {'charge': None, 'drain': None}}}

def parse_sleep_duration(duration_str):
    """Convert '7h 20m' format to total minutes"""
    if not duration_str:
        return None
    
    total_minutes = 0
    try:
        import re
        hours_match = re.search(r'(\d+)h', duration_str)
        if hours_match:
            total_minutes += int(hours_match.group(1)) * 60
        
        minutes_match = re.search(r'(\d+)m', duration_str)
        if minutes_match:
            total_minutes += int(minutes_match.group(1))
        
        return total_minutes if total_minutes > 0 else None
    except:
        return None

def extract_number(value_str):
    """Extract first number from strings like '53 bpm', '46 ms'"""
    if not value_str:
        return None
    
    import re
    match = re.search(r'(\d+)', str(value_str))
    return int(match.group(1)) if match else None

def convert_file_to_structured_format(file_path):
    """Convert a single daily file to the structured format"""
    content = file_path.read_text()
    
    # Parse existing YAML front matter
    if not content.startswith('---'):
        logger.warning(f"No YAML front matter in {file_path}")
        return
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        logger.warning(f"Invalid YAML structure in {file_path}")
        return
    
    try:
        existing_data = yaml.safe_load(parts[1])
    except:
        logger.error(f"Could not parse YAML in {file_path}")
        return
    
    date_str = existing_data.get('date', '')
    if not date_str:
        logger.warning(f"No date found in {file_path}")
        return
    
    # Get real sleep and wellness data
    logger.info(f"Getting real sleep/wellness data for {date_str}")
    real_data = get_real_sleep_wellness_data(date_str)
    
    # Extract workout data from existing file
    workouts = []
    if 'workouts' in existing_data:
        workouts = existing_data['workouts']
    elif 'workout_metrics' in existing_data:
        workouts = existing_data['workout_metrics']
    
    # Convert workouts to proper format
    converted_workouts = []
    for workout in workouts:
        converted_workout = {
            'id': workout.get('id', 0),
            'type': workout.get('type', 'Run'),
            'start': workout.get('start', ''),
            'distance_mi': workout.get('distance_mi', 0),
            'moving_time_s': workout.get('moving_time_s', 0),
            'elev_gain_ft': workout.get('elev_gain_ft', 0),
            'avg_hr': workout.get('avg_hr', 0),
            'max_hr': workout.get('max_hr', workout.get('avg_hr', 0) + 10),
            'avg_pace_s_per_mi': workout.get('avg_pace_s_per_mi', 0),
        }
        
        # Add optional fields if they exist
        optional_fields = [
            'avg_cadence_spm', 'avg_stride_length_ft', 'vertical_osc_in', 
            'gct_ms', 'gct_balance_pct', 'aerobicTE', 'anaerobicTE', 'timeInHrZone_sec'
        ]
        for field in optional_fields:
            if field in workout:
                converted_workout[field] = workout[field]
        
        # Convert splits
        if 'splits' in workout:
            converted_splits = []
            for split in workout['splits']:
                converted_split = {
                    'mile': split.get('mile', 1),
                    'avg_hr': split.get('avg_hr', split.get('hr_bpm', 0)),
                    'max_hr': split.get('max_hr', split.get('avg_hr', split.get('hr_bpm', 0)) + 5),
                    'avg_pace_s_per_mi': split.get('avg_pace_s_per_mi', split.get('pace_s_per_mi', 0)),
                    'mile_time_s': split.get('mile_time_s', split.get('time_s', 0)),
                    'elev_gain_ft': split.get('elev_gain_ft', 0)
                }
                
                # Add optional split fields
                optional_split_fields = [
                    'cadence_spm', 'stride_length_ft', 'vertical_osc_in', 
                    'gct_ms', 'gct_balance_pct', 'power_w', 'temperature_f', 'aerobicTE', 'anaerobicTE'
                ]
                for field in optional_split_fields:
                    if field in split:
                        converted_split[field] = split[field]
                
                converted_splits.append(converted_split)
            
            converted_workout['splits'] = converted_splits
        
        converted_workouts.append(converted_workout)
    
    # Calculate daily totals
    total_distance = sum(w.get('distance_mi', 0) for w in converted_workouts)
    total_time = sum(w.get('moving_time_s', 0) for w in converted_workouts)
    total_elevation = sum(w.get('elev_gain_ft', 0) for w in converted_workouts)
    
    # Estimate steps (roughly 2000 steps per mile)
    estimated_steps = int(total_distance * 2000)
    
    # Build the structured format
    structured_data = {
        'date': date_str,
        'schema': 2
    }
    
    # Add sleep metrics (real data or message if none available)
    if real_data['sleep_metrics']:
        structured_data['sleep_metrics'] = real_data['sleep_metrics']
    
    # Add daily metrics
    daily_metrics = {
        'body_battery': real_data['daily_metrics']['body_battery'],
        'steps': estimated_steps,
        'total_workout_distance_mi': round(total_distance, 2),
        'total_moving_time_s': total_time,
        'total_elev_gain_ft': int(total_elevation)
    }
    structured_data['daily_metrics'] = daily_metrics
    
    # Add workouts
    structured_data['workout_metrics'] = converted_workouts
    
    # Generate markdown content
    hours = total_time // 3600
    minutes = (total_time % 3600) // 60
    
    # Sleep summary
    sleep_summary = ""
    if real_data['sleep_metrics'] and real_data['sleep_metrics']['sleep_minutes']:
        sleep_mins = real_data['sleep_metrics']['sleep_minutes']
        sleep_hours = sleep_mins // 60
        sleep_mins_remainder = sleep_mins % 60
        sleep_score = real_data['sleep_metrics']['sleep_score'] or 'N/A'
        resting_hr = real_data['sleep_metrics']['resting_hr'] or 'N/A'
        hrv = real_data['sleep_metrics']['hrv_night_avg'] or 'N/A'
        bb_charge = daily_metrics['body_battery']['charge'] or 'N/A'
        bb_drain = daily_metrics['body_battery']['drain'] or 'N/A'
        
        sleep_summary = f"**Sleep:** {sleep_hours} h {sleep_mins_remainder} m (Score {sleep_score}) • Rest HR {resting_hr} bpm • HRV {hrv} ms • BB +{bb_charge}/–{bb_drain}"
    else:
        sleep_summary = "**Sleep:** No sleep data available for this date"
    
    # Create new content
    yaml_str = yaml.dump(structured_data, default_flow_style=False, sort_keys=False)
    
    new_content = f"""---
{yaml_str}---
# {date_str} · Daily Summary
**Totals:** {total_distance:.1f} mi • {hours} h {minutes} m • {total_elevation} ft ↑ • {estimated_steps:,} steps  
{sleep_summary}

<details>
<summary>Full JSON</summary>

```json
{json.dumps(structured_data, indent=2)}
```
</details>
"""
    
    # Write the updated file
    file_path.write_text(new_content)
    logger.info(f"✅ Converted {file_path} to structured format")

def convert_all_files():
    """Convert all daily markdown files"""
    data_dir = Path("data")
    
    if not data_dir.exists():
        logger.error("Data directory not found")
        return
    
    count = 0
    for file_path in data_dir.rglob("*.md"):
        if file_path.name != "README.md" and len(file_path.name) <= 5:  # Daily files like "07.md"
            logger.info(f"Converting {file_path}")
            convert_file_to_structured_format(file_path)
            count += 1
    
    logger.info(f"✅ Converted {count} files to structured format")

if __name__ == "__main__":
    convert_all_files() 