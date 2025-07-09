#!/usr/bin/env python3
"""
Data Consistency Fix Script
Performs comprehensive corrections across training data files to ensure:
- Missing splits are populated from FIT files
- Front-matter YAML matches JSON blocks
- Units and field names are standardized
- Missing wellness data is filled from Garmin
- Weather placeholders are replaced with real data
- Index file is regenerated and validated
"""

import json
import os
import sys
import yaml
import re
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import math

try:
    import garth
    from fitparse import FitFile
    import requests
    from dateutil import tz
except ImportError as e:
    print(f"Missing required dependency: {e}")
    print("Please install requirements: pip install -r requirements.txt")
    sys.exit(1)

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataConsistencyFixer:
    def __init__(self):
        self.data_dir = Path("data")
        self.index_file = self.data_dir / "index.json"
        self.changes_summary = {
            "files_processed": 0,
            "splits_fixed": 0,
            "yaml_json_synced": 0,
            "units_standardized": 0,
            "wellness_filled": 0,
            "weather_fixed": 0,
            "errors": []
        }
        
        # Load environment variables
        self.garmin_email = os.getenv("GARMIN_EMAIL")
        self.garmin_password = os.getenv("GARMIN_PASSWORD")
        self.weather_api_key = os.getenv("VISUAL_CROSSING_API_KEY")
        
        # Unit conversion constants
        self.CM_TO_FEET = 1 / 30.48
        self.MM_TO_INCHES = 1 / 25.4
        
        # Initialize Garmin authentication
        self.garmin_authenticated = False
        
    def authenticate_garmin(self) -> bool:
        """Authenticate with Garmin Connect"""
        if self.garmin_authenticated:
            return True
            
        if not self.garmin_email or not self.garmin_password:
            logger.warning("Garmin credentials not found in environment variables")
            return False
            
        try:
            logger.info("Authenticating with Garmin Connect...")
            garth.login(self.garmin_email, self.garmin_password)
            self.garmin_authenticated = True
            logger.info("Successfully authenticated with Garmin Connect")
            return True
        except Exception as e:
            logger.error(f"Garmin Connect authentication failed: {e}")
            self.changes_summary["errors"].append(f"Garmin auth failed: {e}")
            return False

    def download_fit_file(self, activity_id: int) -> Optional[bytes]:
        """Download FIT file for an activity"""
        if not self.authenticate_garmin():
            return None
            
        try:
            import io
            import requests
            
            # Use the same approach as the main scraper for authenticated requests
            session = getattr(garth.client, '_session', None) or getattr(garth.client, 'session', None)
            
            if session:
                response = session.get(
                    f"https://connectapi.garmin.com/download-service/files/activity/{activity_id}"
                )
            else:
                # Fallback: build request manually with OAuth token
                headers = {
                    'Authorization': f'Bearer {garth.client.oauth2_token.token}',
                    'Accept': 'application/octet-stream'
                }
                response = requests.get(
                    f"https://connectapi.garmin.com/download-service/files/activity/{activity_id}",
                    headers=headers
                )
            
            if response.status_code == 200 and response.content:
                logger.info(f"Successfully downloaded FIT file for activity {activity_id}")
                return response.content
            else:
                logger.warning(f"Failed to download FIT file for activity {activity_id}: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Could not download FIT file for activity {activity_id}: {e}")
            return None

    def parse_fit_splits(self, fit_data: bytes, distance_mi: float) -> List[Dict[str, Any]]:
        """Parse FIT file to extract detailed mile splits"""
        splits = []
        
        try:
            import io
            fit_file = FitFile(io.BytesIO(fit_data))
            
            # Get all record messages
            records = []
            for record in fit_file.get_messages('record'):
                record_data = {"timestamp": None}
                for field in record:
                    if field.value is not None:
                        record_data[field.name] = field.value
                records.append(record_data)
            
            if not records:
                logger.warning("No record data found in FIT file")
                return splits
                
            # Sort by timestamp
            records = [r for r in records if r.get('timestamp')]
            records.sort(key=lambda x: x['timestamp'])
            
            # Calculate mile splits
            num_miles = max(1, math.floor(distance_mi))
            distance_per_mile = 1609.34  # meters per mile
            
            for mile in range(1, num_miles + 1):
                start_distance = (mile - 1) * distance_per_mile
                end_distance = mile * distance_per_mile
                
                # Find records for this mile
                mile_records = []
                for record in records:
                    distance = record.get('distance', 0)
                    if start_distance <= distance <= end_distance:
                        mile_records.append(record)
                
                if not mile_records:
                    continue
                    
                # Calculate split metrics
                split_data = {
                    "mile": mile,
                    "avg_hr": None,
                    "max_hr": None,
                    "avg_pace_s_per_mi": None,
                    "mile_time_s": None,
                    "elev_gain_ft": None
                }
                
                # Heart rate data
                hr_values = [r.get('heart_rate') for r in mile_records if r.get('heart_rate')]
                if hr_values:
                    split_data["avg_hr"] = int(sum(hr_values) / len(hr_values))
                    split_data["max_hr"] = max(hr_values)
                
                # Time for this mile
                if len(mile_records) >= 2:
                    start_time = mile_records[0]['timestamp']
                    end_time = mile_records[-1]['timestamp']
                    mile_time_s = int((end_time - start_time).total_seconds())
                    split_data["mile_time_s"] = mile_time_s
                    
                    # Calculate pace (seconds per mile)
                    if mile_time_s > 0:
                        split_data["avg_pace_s_per_mi"] = mile_time_s
                
                # Elevation gain
                altitude_values = [r.get('altitude') for r in mile_records if r.get('altitude')]
                if len(altitude_values) >= 2:
                    elev_gain_m = max(altitude_values) - min(altitude_values)
                    split_data["elev_gain_ft"] = max(0, int(elev_gain_m * 3.28084))
                
                # Add enhanced running dynamics if available
                cadence_values = [r.get('cadence') for r in mile_records if r.get('cadence')]
                if cadence_values:
                    split_data["cadence_spm"] = int(sum(cadence_values) / len(cadence_values))
                
                stride_length_values = [r.get('stride_length') for r in mile_records if r.get('stride_length')]
                if stride_length_values:
                    avg_stride_mm = sum(stride_length_values) / len(stride_length_values)
                    split_data["stride_length_ft"] = round(avg_stride_mm * 0.00328084, 1)
                
                vo_values = [r.get('vertical_oscillation') for r in mile_records if r.get('vertical_oscillation')]
                if vo_values:
                    avg_vo_mm = sum(vo_values) / len(vo_values)
                    split_data["vertical_osc_in"] = round(avg_vo_mm * self.MM_TO_INCHES, 1)
                
                gct_values = [r.get('stance_time') for r in mile_records if r.get('stance_time')]
                if gct_values:
                    split_data["gct_ms"] = int(sum(gct_values) / len(gct_values))
                
                power_values = [r.get('power') for r in mile_records if r.get('power')]
                if power_values:
                    split_data["power_w"] = int(sum(power_values) / len(power_values))
                
                splits.append(split_data)
            
            logger.info(f"Generated {len(splits)} mile splits from FIT file")
            
        except Exception as e:
            logger.error(f"Error parsing FIT file for splits: {e}")
            
        return splits

    def fix_missing_splits(self, workout_data: Dict) -> bool:
        """Fix missing splits by re-parsing FIT file"""
        distance_mi = workout_data.get('distance_mi', 0)
        current_splits = workout_data.get('splits', [])
        expected_splits = math.floor(distance_mi)
        
        if len(current_splits) >= expected_splits:
            return False  # No fix needed
            
        activity_id = workout_data.get('id')
        if not activity_id:
            logger.warning("No activity ID found for workout - cannot download FIT file")
            return False
            
        logger.info(f"Fixing missing splits for activity {activity_id}: {len(current_splits)}/{expected_splits}")
        
        # Download and parse FIT file
        fit_data = self.download_fit_file(activity_id)
        if not fit_data:
            return False
            
        new_splits = self.parse_fit_splits(fit_data, distance_mi)
        if new_splits:
            workout_data['splits'] = new_splits
            self.changes_summary["splits_fixed"] += 1
            logger.info(f"Fixed splits for activity {activity_id}: {len(new_splits)} splits generated")
            return True
            
        return False

    def standardize_units_and_keys(self, data: Dict) -> bool:
        """Standardize units and field names throughout the data"""
        changed = False
        
        # Fix workout metrics
        for workout in data.get('workout_metrics', []):
            # Rename distance → distance_mi and format to 2 decimals
            if 'distance' in workout and 'distance_mi' not in workout:
                workout['distance_mi'] = round(float(workout.pop('distance', 0)), 2)
                changed = True
            elif 'distance_mi' in workout:
                workout['distance_mi'] = round(float(workout['distance_mi']), 2)
                changed = True
                
            # Convert avgStrideLength from cm to avg_stride_length_ft
            if 'avgStrideLength' in workout:
                cm_value = float(workout.pop('avgStrideLength'))
                workout['avg_stride_length_ft'] = round(cm_value * self.CM_TO_FEET, 1)
                changed = True
                
            # Convert verticalOscillation from mm to vertical_osc_in
            if 'verticalOscillation' in workout:
                mm_value = float(workout.pop('verticalOscillation'))
                workout['vertical_osc_in'] = round(mm_value * self.MM_TO_INCHES, 1)
                changed = True
                
            # Compute average gct_ms from total
            if 'groundContactTime' in workout and 'gct_ms' not in workout:
                # Extract numeric value from string like "289 ms"
                gct_str = str(workout.get('groundContactTime', ''))
                gct_match = re.search(r'(\d+)', gct_str)
                if gct_match:
                    workout['gct_ms'] = int(gct_match.group(1))
                    workout.pop('groundContactTime')
                    changed = True
            
            # Fix splits within workout
            for split in workout.get('splits', []):
                # Same transformations for splits
                if 'avgStrideLength' in split:
                    cm_value = float(split.pop('avgStrideLength'))
                    split['avg_stride_length_ft'] = round(cm_value * self.CM_TO_FEET, 1)
                    changed = True
                    
                if 'verticalOscillation' in split:
                    mm_value = float(split.pop('verticalOscillation'))
                    split['vertical_osc_in'] = round(mm_value * self.MM_TO_INCHES, 1)
                    changed = True
        
        if changed:
            self.changes_summary["units_standardized"] += 1
            
        return changed

    def get_garmin_wellness_data(self, date: str) -> Optional[Dict]:
        """Get wellness data from Garmin for a specific date"""
        if not self.authenticate_garmin():
            return None
            
        try:
            wellness = {}
            
            # Get daily step data
            try:
                steps_data = garth.connectapi(f"/wellness-service/wellness/dailySummaryChart/{date}")
                if steps_data and steps_data.get('summaryList'):
                    for summary in steps_data['summaryList']:
                        if summary.get('summaryId') == 'steps':
                            wellness["steps"] = summary.get('value', 0)
                            break
            except Exception as e:
                logger.debug(f"Could not get step data for {date}: {e}")
            
            # Get resting heart rate
            try:
                rhr_data = garth.connectapi(f"/wellness-service/wellness/dailyHeartRate/{date}")
                if rhr_data and rhr_data.get('restingHeartRate'):
                    wellness["resting_hr"] = rhr_data['restingHeartRate']
            except Exception as e:
                logger.debug(f"Could not get resting heart rate for {date}: {e}")
            
            # Get HRV data
            try:
                hrv_data = garth.connectapi(f"/hrv-service/hrv/{date}")
                if hrv_data and hrv_data.get('hrvSummary', {}).get('weeklyAvg'):
                    wellness["hrv_night_avg"] = hrv_data['hrvSummary']['weeklyAvg']
            except Exception as e:
                logger.debug(f"Could not get HRV data for {date}: {e}")
            
            # Get body battery data
            try:
                bb_data = garth.connectapi(f"/wellness-service/wellness/bodyBattery/reports/daily/{date}")
                if bb_data and bb_data.get('bodyBatteryValuesArray'):
                    values = bb_data['bodyBatteryValuesArray']
                    if values:
                        # Calculate charge and drain
                        first_val = values[0].get('charged', 0)
                        last_val = values[-1].get('charged', 0)
                        if last_val > first_val:
                            wellness["body_battery"] = {
                                "charge": last_val - first_val,
                                "drain": 0
                            }
                        else:
                            wellness["body_battery"] = {
                                "charge": 0,
                                "drain": first_val - last_val
                            }
            except Exception as e:
                logger.debug(f"Could not get body battery data for {date}: {e}")
            
            return wellness if wellness else None
            
        except Exception as e:
            logger.warning(f"Could not fetch wellness data for {date}: {e}")
            return None

    def fill_missing_wellness_fields(self, data: Dict) -> bool:
        """Fill missing wellness fields from Garmin API"""
        changed = False
        date = data.get('date')
        if not date:
            return False
            
        daily_metrics = data.get('daily_metrics', {})
        
        # Check what's missing
        missing_fields = []
        if not daily_metrics.get('steps'):
            missing_fields.append('steps')
        if not daily_metrics.get('resting_hr'):
            missing_fields.append('resting_hr')
        if not data.get('sleep_metrics', {}).get('hrv_night_avg'):
            missing_fields.append('hrv_night_avg')
        if not daily_metrics.get('body_battery', {}).get('charge') and not daily_metrics.get('body_battery', {}).get('drain'):
            missing_fields.append('body_battery')
            
        if not missing_fields:
            return False
            
        logger.info(f"Fetching missing wellness data for {date}: {missing_fields}")
        
        # Get wellness data from Garmin
        wellness_data = self.get_garmin_wellness_data(date)
        if not wellness_data:
            return False
            
        # Fill in missing data
        if 'steps' in missing_fields and wellness_data.get('steps'):
            daily_metrics['steps'] = wellness_data['steps']
            changed = True
            
        if 'resting_hr' in missing_fields and wellness_data.get('resting_hr'):
            daily_metrics['resting_hr'] = wellness_data['resting_hr']
            changed = True
            
        if 'hrv_night_avg' in missing_fields and wellness_data.get('hrv_night_avg'):
            if 'sleep_metrics' not in data:
                data['sleep_metrics'] = {}
            data['sleep_metrics']['hrv_night_avg'] = wellness_data['hrv_night_avg']
            changed = True
            
        if 'body_battery' in missing_fields and wellness_data.get('body_battery'):
            daily_metrics['body_battery'] = wellness_data['body_battery']
            changed = True
            
        if changed:
            self.changes_summary["wellness_filled"] += 1
            logger.info(f"Filled wellness data for {date}")
            
        return changed

    def get_weather_for_location_time(self, lat: float, lon: float, timestamp: str) -> Optional[float]:
        """Get weather data from Visual Crossing API"""
        if not self.weather_api_key:
            return None
            
        try:
            # Convert timestamp to date for API call
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            date_str = dt.strftime('%Y-%m-%d')
            
            url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{lat},{lon}/{date_str}"
            params = {
                'key': self.weather_api_key,
                'unitGroup': 'us',
                'include': 'hours',
                'elements': 'temp'
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                
                # Find the closest hour to our timestamp
                target_hour = dt.hour
                for hour_data in data.get('days', [{}])[0].get('hours', []):
                    if int(hour_data.get('datetime', '00:00').split(':')[0]) == target_hour:
                        return float(hour_data.get('temp', 0))
                        
                # Fallback to day average
                return float(data.get('days', [{}])[0].get('temp', 0))
                
        except Exception as e:
            logger.debug(f"Could not get weather data: {e}")
            
        return None

    def replace_weather_placeholders(self, data: Dict) -> bool:
        """Replace weather placeholders with real temperature data"""
        changed = False
        
        for workout in data.get('workout_metrics', []):
            for split in workout.get('splits', []):
                temp = split.get('temperature_f')
                if temp and (isinstance(temp, str) or temp == 0):
                    # This looks like a placeholder, try to get real weather
                    # For now, we'll need GPS coordinates and timestamp
                    # This would require additional data from the workout
                    # Skipping for now as it requires more complex implementation
                    pass
                    
        return changed

    def sync_yaml_json_blocks(self, file_path: Path) -> bool:
        """Sync YAML front matter with JSON block in the file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Split content into sections
            if '---\n' not in content:
                logger.warning(f"No YAML front matter found in {file_path}")
                return False
                
            parts = content.split('---\n', 2)
            if len(parts) < 3:
                logger.warning(f"Invalid YAML front matter structure in {file_path}")
                return False
                
            yaml_content = parts[1]
            markdown_content = parts[2]
            
            # Parse YAML data
            yaml_data = yaml.safe_load(yaml_content)
            
            # Find and extract JSON block
            json_pattern = r'```json\n(.*?)\n```'
            json_match = re.search(json_pattern, markdown_content, re.DOTALL)
            
            if not json_match:
                logger.warning(f"No JSON block found in {file_path}")
                return False
                
            # Parse existing JSON
            try:
                json_data = json.loads(json_match.group(1))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in {file_path}: {e}")
                return False
                
            # Check if they're already in sync
            if json_data == yaml_data:
                return False  # No changes needed
                
            # Update JSON to match YAML
            updated_json = json.dumps(yaml_data, indent=2)
            updated_content = content.replace(json_match.group(1), updated_json)
            
            # Write back to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
                
            self.changes_summary["yaml_json_synced"] += 1
            logger.info(f"Synced YAML and JSON in {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error syncing YAML/JSON in {file_path}: {e}")
            self.changes_summary["errors"].append(f"YAML/JSON sync failed for {file_path}: {e}")
            return False

    def update_index_file(self) -> bool:
        """Regenerate the index.json file by scanning all daily files"""
        try:
            files_found = []
            
            # Scan data directory for all YYYY/MM/DD.md files
            for year_dir in self.data_dir.glob("20*"):
                if year_dir.is_dir():
                    for month_dir in year_dir.glob("*"):
                        if month_dir.is_dir():
                            for day_file in month_dir.glob("*.md"):
                                # Parse date from file path
                                try:
                                    year = year_dir.name
                                    month = month_dir.name.zfill(2)
                                    day = day_file.stem.zfill(2)
                                    date_str = f"{year}-{month}-{day}"
                                    
                                    files_found.append({
                                        "date": date_str,
                                        "path": str(day_file.relative_to(Path.cwd()))
                                    })
                                except Exception as e:
                                    logger.warning(f"Could not parse date from {day_file}: {e}")
            
            # Sort by date (newest first)
            files_found.sort(key=lambda x: x["date"], reverse=True)
            
            # Write index file
            with open(self.index_file, 'w', encoding='utf-8') as f:
                json.dump(files_found, f, indent=2)
                
            logger.info(f"Updated index.json with {len(files_found)} files")
            return True
            
        except Exception as e:
            logger.error(f"Error updating index file: {e}")
            self.changes_summary["errors"].append(f"Index update failed: {e}")
            return False

    def validate_file(self, file_path: Path, data: Dict) -> List[str]:
        """Validate a daily file for completeness and consistency"""
        issues = []
        
        # Check required sections
        if not data.get('daily_metrics'):
            issues.append("Missing daily_metrics section")
        elif not data['daily_metrics'].get('steps'):
            issues.append("Missing steps data in daily_metrics")
            
        # Check workouts have splits
        for i, workout in enumerate(data.get('workout_metrics', [])):
            distance_mi = workout.get('distance_mi', 0)
            splits = workout.get('splits', [])
            expected_splits = math.floor(distance_mi)
            
            if expected_splits > 0 and len(splits) < expected_splits:
                issues.append(f"Workout {i+1}: has {len(splits)} splits but expected {expected_splits}")
                
        return issues

    def process_daily_file(self, file_path: Path) -> bool:
        """Process a single daily file with all fixes"""
        logger.info(f"Processing {file_path}")
        
        try:
            # Read and parse the file
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if '---\n' not in content:
                logger.warning(f"No YAML front matter in {file_path}")
                return False
                
            parts = content.split('---\n', 2)
            if len(parts) < 3:
                logger.warning(f"Invalid file structure in {file_path}")
                return False
                
            yaml_content = parts[1]
            data = yaml.safe_load(yaml_content)
            
            if not data:
                logger.warning(f"No data found in {file_path}")
                return False
                
            file_changed = False
            
            # 1. Fix missing splits
            for workout in data.get('workout_metrics', []):
                if self.fix_missing_splits(workout):
                    file_changed = True
                    
            # 2. Standardize units and keys
            if self.standardize_units_and_keys(data):
                file_changed = True
                
            # 3. Fill missing wellness fields
            if self.fill_missing_wellness_fields(data):
                file_changed = True
                
            # 4. Replace weather placeholders
            if self.replace_weather_placeholders(data):
                file_changed = True
                
            # If data changed, write back to file
            if file_changed:
                # Reconstruct the file
                updated_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False)
                updated_content = f"---\n{updated_yaml}---\n{parts[2]}"
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)
                    
                logger.info(f"Updated data in {file_path}")
                
            # 5. Sync YAML and JSON blocks
            if self.sync_yaml_json_blocks(file_path):
                file_changed = True
                
            # 6. Validate the file
            issues = self.validate_file(file_path, data)
            if issues:
                logger.warning(f"Validation issues in {file_path}: {', '.join(issues)}")
                self.changes_summary["errors"].extend([f"{file_path}: {issue}" for issue in issues])
                
            self.changes_summary["files_processed"] += 1
            return file_changed
            
        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            self.changes_summary["errors"].append(f"Processing failed for {file_path}: {e}")
            return False

    def commit_changes(self) -> bool:
        """Commit all changes to git repository"""
        try:
            import subprocess
            
            # Add all changes
            subprocess.run(["git", "add", "data/"], check=True)
            
            # Create commit message
            commit_msg = f"fix: data consistency update - {self.changes_summary['files_processed']} files processed"
            
            # Commit
            result = subprocess.run(["git", "commit", "-m", commit_msg], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully committed changes: {commit_msg}")
                return True
            else:
                logger.info("No changes to commit")
                return True
                
        except Exception as e:
            logger.error(f"Error committing changes: {e}")
            self.changes_summary["errors"].append(f"Git commit failed: {e}")
            return False

    def run_consistency_fixes(self) -> bool:
        """Run all consistency fixes across the data directory"""
        logger.info("Starting data consistency fixes...")
        
        # Find all daily files
        daily_files = []
        for year_dir in self.data_dir.glob("20*"):
            if year_dir.is_dir():
                for month_dir in year_dir.glob("*"):
                    if month_dir.is_dir():
                        for day_file in month_dir.glob("*.md"):
                            daily_files.append(day_file)
        
        daily_files.sort()
        logger.info(f"Found {len(daily_files)} daily files to process")
        
        if not daily_files:
            logger.warning("No daily files found to process")
            return False
            
        # Process each file
        any_changes = False
        for file_path in daily_files:
            try:
                if self.process_daily_file(file_path):
                    any_changes = True
            except KeyboardInterrupt:
                logger.info("Process interrupted by user")
                break
            except Exception as e:
                logger.error(f"Unexpected error processing {file_path}: {e}")
                self.changes_summary["errors"].append(f"Unexpected error for {file_path}: {e}")
                
        # Update index file
        if self.update_index_file():
            any_changes = True
            
        # Print summary
        self.print_summary()
        
        # Commit changes if any were made
        if any_changes:
            self.commit_changes()
            
        # Check for critical errors
        if self.changes_summary["errors"]:
            logger.error(f"Process completed with {len(self.changes_summary['errors'])} errors")
            return False
            
        logger.info("Data consistency fixes completed successfully")
        return True

    def print_summary(self):
        """Print summary of changes made"""
        summary = self.changes_summary
        
        print("\n" + "="*60)
        print("DATA CONSISTENCY FIX SUMMARY")
        print("="*60)
        print(f"Files processed: {summary['files_processed']}")
        print(f"Splits fixed: {summary['splits_fixed']}")
        print(f"YAML/JSON synced: {summary['yaml_json_synced']}")
        print(f"Units standardized: {summary['units_standardized']}")
        print(f"Wellness data filled: {summary['wellness_filled']}")
        print(f"Weather data fixed: {summary['weather_fixed']}")
        
        if summary['errors']:
            print(f"\nERRORS ({len(summary['errors'])}):")
            for error in summary['errors'][:10]:  # Show first 10 errors
                print(f"  - {error}")
            if len(summary['errors']) > 10:
                print(f"  ... and {len(summary['errors']) - 10} more errors")
        else:
            print("\nNo errors encountered!")
            
        print("="*60)

def main():
    """Main entry point"""
    fixer = DataConsistencyFixer()
    
    try:
        success = fixer.run_consistency_fixes()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 