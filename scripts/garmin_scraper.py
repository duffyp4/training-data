#!/usr/bin/env python3
"""
Garmin Connect Scraper
Replaces the Strava scraper with direct API calls to Garmin Connect
Maintains backward compatibility with existing data format
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

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

class GarminScraper:
    def __init__(self):
        self.client = None
        self.data_dir = Path("data")
        self.last_id_file = self.data_dir / "last_id.json"
        self.activities_output = Path("activities.json")
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)
        
        # Garmin credentials from environment
        self.email = os.getenv("GARMIN_EMAIL")
        self.password = os.getenv("GARMIN_PASSWORD")
        
        if not self.email or not self.password:
            raise ValueError("GARMIN_EMAIL and GARMIN_PASSWORD environment variables must be set")

    def authenticate(self) -> bool:
        """Authenticate with Garmin Connect"""
        try:
            logger.info("Authenticating with Garmin Connect...")
            garth.login(self.email, self.password)
            logger.info("Successfully authenticated with Garmin Connect")
            return True
        except Exception as e:
            logger.error(f"Garmin Connect authentication failed: {e}")
            return False

    def get_last_processed(self) -> Dict[str, Optional[str]]:
        """Read the last processed activity ID and date"""
        try:
            if self.last_id_file.exists():
                with open(self.last_id_file, 'r') as f:
                    data = json.load(f)
                    last_id = data.get("last_id")
                    last_date = data.get("last_date")
                    
                    # Check if we're transitioning from Strava to Garmin
                    if last_id and len(last_id) == 11 and last_id.isdigit():
                        # This is a Strava ID - we're in transition mode
                        logger.info(f"Detected Strava ID {last_id} - transition mode enabled")
                        logger.info("Will use date-based filtering for first Garmin sync")
                        return {
                            "id": None,  # Ignore Strava ID for Garmin comparison
                            "date": last_date,
                            "transition_mode": True,
                            "strava_id": last_id
                        }
                    
                    return {
                        "id": last_id,
                        "date": last_date,
                        "transition_mode": False
                    }
        except Exception as e:
            logger.warning(f"Could not read last_id.json: {e}")
        
        return {"id": None, "date": None, "transition_mode": False}

    def is_activity_newer(self, activity_date: str, last_date: Optional[str]) -> bool:
        """Check if an activity date is newer than the last processed date"""
        if not last_date:
            return True
        
        try:
            # Parse Garmin date format - handle both full timestamps and date-only
            if 'T' in activity_date or ' ' in activity_date:
                # Garmin format with timestamp: "2025-07-07T08:08:43" or "2025-07-07 08:08:43"
                activity_date_only = activity_date.split('T')[0].split(' ')[0]
            else:
                # Already just date: "2025-07-07"
                activity_date_only = activity_date
            
            activity_dt = datetime.strptime(activity_date_only, "%Y-%m-%d")
            
            # Parse last date format - handle multiple possible formats
            if ',' in last_date:
                # Strava format: "Tue, 7/1/2025"
                date_part = last_date.split(',')[1].strip()
                last_dt = datetime.strptime(date_part, "%m/%d/%Y")
            elif 'T' in last_date or (' ' in last_date and ':' in last_date):
                # Garmin timestamp format: "2025-07-06 14:29:18" or "2025-07-06T14:29:18"
                last_date_only = last_date.split('T')[0].split(' ')[0]
                last_dt = datetime.strptime(last_date_only, "%Y-%m-%d")
            else:
                # Simple date format: "2025-07-06"
                last_dt = datetime.strptime(last_date, "%Y-%m-%d")
            
            # Only include activities AFTER the last date (not same day)
            is_newer = activity_dt > last_dt
            logger.info(f"Date comparison: {activity_date_only} > {last_dt.strftime('%Y-%m-%d')} = {is_newer}")
            return is_newer
        except Exception as e:
            logger.warning(f"Could not parse dates for comparison: activity='{activity_date}', last='{last_date}': {e}")
            # FIXED: Default to excluding the activity when date parsing fails (safer)
            # This prevents processing old activities when date formats are unclear
            return False

    def get_activities_since_date(self, start_date: datetime) -> List[Dict]:
        """Get activities from Garmin Connect since a specific date"""
        try:
            # Get activities from the last 30 days to ensure we catch everything
            activities = garth.connectapi("/activitylist-service/activities/search/activities", params={"limit": 100})  # Get last 100 activities
            
            # Filter to only activities newer than our last processed
            new_activities = []
            last_processed = self.get_last_processed()
            
            for activity in activities:
                activity_id = activity.get('activityId')
                activity_date = activity.get('startTimeLocal', '').split('T')[0]
                
                logger.debug(f"Evaluating activity {activity_id} from {activity_date}")
                
                # Handle transition mode vs normal mode
                if last_processed.get("transition_mode"):
                    # Transition mode: Use date-based filtering only, ignore ID comparison
                    if activity_date and self.is_activity_newer(activity_date, last_processed["date"]):
                        logger.info(f"Adding activity {activity_id} (transition mode - newer than {last_processed['date']})")
                        new_activities.append(activity)
                    else:
                        logger.debug(f"Skipping activity {activity_id} (not newer than last Strava date)")
                else:
                    # Normal mode: Check Garmin ID comparison
                    if last_processed["id"] and str(activity_id) == last_processed["id"]:
                        logger.info(f"Found last processed Garmin activity {activity_id}. Stopping.")
                        break
                    elif activity_date and self.is_activity_newer(activity_date, last_processed["date"]):
                        logger.info(f"Adding activity {activity_id} (normal mode)")
                        new_activities.append(activity)
                    else:
                        logger.debug(f"Skipping activity {activity_id} (already processed)")
            
            logger.info(f"Found {len(new_activities)} new activities to process")
            return new_activities
            
        except Exception as e:
            logger.error(f"Error fetching activities: {e}")
            return []

    def download_fit_file(self, activity_id: int) -> Optional[bytes]:
        """Download FIT file for an activity"""
        try:
            # FIT files are binary data, so we need to use raw HTTP request
            # Get the session and make a direct request for binary data
            import requests
            
            # Use garth's session to maintain authentication
            response = requests.get(
                f"https://connectapi.garmin.com/download-service/files/activity/{activity_id}",
                headers=garth.client.request_headers(),
                cookies=garth.client.session.cookies
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

    def parse_fit_file(self, fit_data: bytes) -> Dict[str, Any]:
        """Parse FIT file to extract enhanced metrics"""
        enhanced_data = {
            "runningDynamics": {},
            "heartRateData": {},
            "gpsData": {}
        }
        
        try:
            import io
            fit_file = FitFile(io.BytesIO(fit_data))
            
            # Track all record messages for detailed analysis
            records = []
            for record in fit_file.get_messages('record'):
                record_data = {}
                for field in record:
                    if field.value is not None:
                        record_data[field.name] = field.value
                records.append(record_data)
            
            if records:
                # Extract running dynamics
                cadence_values = [r.get('cadence') for r in records if r.get('cadence')]
                if cadence_values:
                    enhanced_data["runningDynamics"]["avgCadence"] = f"{sum(cadence_values) // len(cadence_values)} spm"
                
                # Extract stride length if available (convert from mm to m)
                stride_length_values = [r.get('stride_length') for r in records if r.get('stride_length')]
                if stride_length_values:
                    avg_stride_mm = sum(stride_length_values) / len(stride_length_values)
                    enhanced_data["runningDynamics"]["avgStrideLength"] = f"{round(avg_stride_mm / 1000, 2)} m"
                
                # Extract ground contact time (convert from ms)
                gct_values = [r.get('stance_time') for r in records if r.get('stance_time')]
                if gct_values:
                    enhanced_data["runningDynamics"]["groundContactTime"] = f"{sum(gct_values) // len(gct_values)} ms"
                
                # Extract vertical oscillation (convert from mm to cm)
                vo_values = [r.get('vertical_oscillation') for r in records if r.get('vertical_oscillation')]
                if vo_values:
                    avg_vo_mm = sum(vo_values) / len(vo_values)
                    enhanced_data["runningDynamics"]["verticalOscillation"] = f"{round(avg_vo_mm / 10, 1)} cm"
                
                # Extract power data if available
                power_values = [r.get('power') for r in records if r.get('power')]
                if power_values:
                    enhanced_data["runningDynamics"]["avgPower"] = f"{sum(power_values) // len(power_values)} W"
            
            logger.info("Successfully parsed FIT file for running dynamics")
            
        except Exception as e:
            logger.warning(f"Error parsing FIT file: {e}")
        
        return enhanced_data

    def get_sleep_data(self, date: str) -> Optional[Dict]:
        """Get sleep data for a specific date"""
        try:
            # Use the correct sleep data endpoint format
            sleep_data = garth.connectapi(f"/wellness-service/wellness/dailySleepData", params={"date": date})
            
            if sleep_data and sleep_data.get('dailySleepDTO'):
                sleep_dto = sleep_data['dailySleepDTO']
                result = {}
                
                # Overall sleep score
                if sleep_dto.get('sleepScores'):
                    result["sleepScore"] = sleep_dto['sleepScores'].get('overall', {}).get('value')
                
                # Sleep stages in hours and minutes
                if sleep_dto.get('deepSleepSeconds'):
                    result["deepSleep"] = self.format_sleep_duration(sleep_dto['deepSleepSeconds'])
                if sleep_dto.get('lightSleepSeconds'):
                    result["lightSleep"] = self.format_sleep_duration(sleep_dto['lightSleepSeconds'])
                if sleep_dto.get('remSleepSeconds'):
                    result["remSleep"] = self.format_sleep_duration(sleep_dto['remSleepSeconds'])
                if sleep_dto.get('awakeDurationSeconds'):
                    result["awakeTime"] = self.format_sleep_duration(sleep_dto['awakeDurationSeconds'])
                
                # Total sleep time
                if sleep_dto.get('sleepTimeSeconds'):
                    result["totalSleep"] = self.format_sleep_duration(sleep_dto['sleepTimeSeconds'])
                
                logger.info(f"Successfully retrieved sleep data for {date}")
                return result if result else None
                
        except Exception as e:
            logger.warning(f"Could not fetch sleep data for {date}: {e}")
        return None

    def get_wellness_data(self, date: str) -> Optional[Dict]:
        """Get wellness data for a specific date"""
        try:
            wellness = {}
            
            # Get body battery data
            try:
                bb_data = garth.connectapi(f"/wellness-service/wellness/bodyBattery/reports/daily/{date}")
                if bb_data and bb_data.get('bodyBatteryValuesArray'):
                    # Get the charged value (end of day battery level)
                    values = bb_data['bodyBatteryValuesArray']
                    if values:
                        wellness["bodyBattery"] = values[-1].get('charged')
            except Exception as e:
                logger.debug(f"Could not get body battery data: {e}")
            
            # Get stress data
            try:
                stress_data = garth.connectapi(f"/wellness-service/wellness/dailyStress/{date}")
                if stress_data and stress_data.get('overallStressLevel'):
                    wellness["stressLevel"] = stress_data['overallStressLevel']
            except Exception as e:
                logger.debug(f"Could not get stress data: {e}")
            
            # Get resting heart rate
            try:
                rhr_data = garth.connectapi(f"/wellness-service/wellness/dailyHeartRate/{date}")
                if rhr_data and rhr_data.get('restingHeartRate'):
                    wellness["restingHeartRate"] = f"{rhr_data['restingHeartRate']} bpm"
            except Exception as e:
                logger.debug(f"Could not get resting heart rate: {e}")
            
            # Get HRV data
            try:
                hrv_data = garth.connectapi(f"/hrv-service/hrv/{date}")
                if hrv_data and hrv_data.get('hrvSummary', {}).get('weeklyAvg'):
                    wellness["hrv"] = f"{hrv_data['hrvSummary']['weeklyAvg']} ms"
            except Exception as e:
                logger.debug(f"Could not get HRV data: {e}")
            
            if wellness:
                logger.info(f"Successfully retrieved wellness data for {date}")
                return wellness
            
        except Exception as e:
            logger.warning(f"Could not fetch wellness data for {date}: {e}")
        return None

    def format_sleep_duration(self, seconds: Optional[int]) -> Optional[str]:
        """Convert sleep duration from seconds to human readable format"""
        if not seconds:
            return None
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        return f"{hours}h {minutes}m"

    def convert_garmin_to_strava_format(self, garmin_activity: Dict, enhanced_data: Optional[Dict] = None) -> Dict:
        """Convert Garmin activity format to match existing Strava format"""
        
        # Extract nested data objects
        summary_dto = garmin_activity.get('summaryDTO', {})
        activity_type_dto = garmin_activity.get('activityTypeDTO', {})
        
        # Parse the start time from summaryDTO
        start_time_local = summary_dto.get('startTimeLocal', '')
        if not start_time_local:
            start_time_local = summary_dto.get('startTimeGMT', '')
        
        # Extract date from timestamp
        start_date = ''
        if start_time_local:
            if 'T' in start_time_local:
                start_date = start_time_local.split('T')[0]
            elif ' ' in start_time_local:
                start_date = start_time_local.split(' ')[0]
            else:
                start_date = start_time_local
        
        # Format date to match existing format (e.g., "Tue, 7/1/2025")
        formatted_date = ""
        if start_date:
            try:
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                # Use platform-independent formatting
                month = dt.month
                day = dt.day
                year = dt.year
                day_name = dt.strftime("%a")
                formatted_date = f"{day_name}, {month}/{day}/{year}"
            except Exception as e:
                logger.warning(f"Could not parse date '{start_date}': {e}")
                formatted_date = start_date

        # Extract and format actual start time for JSON-LD
        start_time_iso = ""
        end_time_iso = ""
        
        if start_time_local:
            try:
                # Parse the full Garmin timestamp
                if 'T' in start_time_local:
                    # ISO format: "2025-07-07T14:29:18.000"
                    # Remove any trailing timezone info and add Z for UTC
                    clean_time = start_time_local.split('+')[0].split('-', 3)[0:3]  # Keep date part intact
                    clean_time = '-'.join(clean_time[0:3])
                    if len(start_time_local.split('T')) > 1:
                        time_part = start_time_local.split('T')[1].split('+')[0].split('-')[0]
                        clean_time = clean_time + 'T' + time_part
                    
                    # Ensure it ends with Z for UTC
                    if not clean_time.endswith('Z'):
                        if not clean_time.endswith('.000'):
                            if '.' not in clean_time.split('T')[-1]:
                                clean_time += '.000'
                        clean_time += 'Z'
                    
                    start_time_iso = clean_time
                    
                    # Calculate end time by adding duration
                    duration_s = summary_dto.get('duration', 0)
                    if duration_s and start_time_iso:
                        try:
                            # Parse start time to add duration
                            start_dt = datetime.fromisoformat(start_time_iso.replace('Z', '+00:00'))
                            end_dt = start_dt + timedelta(seconds=int(duration_s))
                            end_time_iso = end_dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
                        except Exception as e:
                            logger.warning(f"Could not calculate end time: {e}")
                            end_time_iso = start_time_iso
                else:
                    # Handle other date formats if needed
                    logger.debug(f"Non-ISO start time format: {start_time_local}")
                    
            except Exception as e:
                logger.warning(f"Could not parse start time '{start_time_local}': {e}")

        # Convert distance from meters to miles
        distance_m = summary_dto.get('distance', 0)
        distance_mi = round(distance_m * 0.000621371, 2) if distance_m else 0
        
        # Convert duration from seconds to MM:SS format  
        duration_s = summary_dto.get('duration', 0)
        # Handle both integer and float duration values
        if duration_s:
            duration_s = int(float(duration_s))  # Convert to int safely
            minutes = duration_s // 60
            seconds = duration_s % 60
            duration_formatted = f"{minutes}:{seconds:02d}"
        else:
            duration_formatted = ""
        
        # Calculate pace (min/mile)
        pace = ""
        if distance_mi > 0 and duration_s > 0:
            pace_s_per_mile = duration_s / distance_mi
            pace_min = int(pace_s_per_mile // 60)
            pace_sec = int(pace_s_per_mile % 60)
            pace = f"{pace_min}:{pace_sec:02d}/mi"

        # Convert elevation from meters to feet
        elevation_m = summary_dto.get('elevationGain', 0)
        elevation_ft = int(round(elevation_m * 3.28084)) if elevation_m else 0
        
        # Get activity type from activityTypeDTO
        type_key = activity_type_dto.get('typeKey', 'unknown')
        
        # Convert activity type to match Strava format
        if "running" in type_key.lower():
            exercise_type = "Run"
        elif "cycling" in type_key.lower():
            exercise_type = "Bike"
        elif "swimming" in type_key.lower():
            exercise_type = "Swim"
        else:
            exercise_type = type_key.title()
        
        # Get workout name
        workout_name = garmin_activity.get('activityName', f"{exercise_type}")
        
        # Base activity data in Strava format
        strava_format = {
            "activityId": str(garmin_activity.get('activityId', '')),
            "sport": exercise_type,
            "date": formatted_date,
            "workoutName": workout_name,
            "duration": duration_formatted,
            "distance": f"{distance_mi:.2f} mi" if distance_mi else "",
            "elevation": f"{elevation_ft} ft",
            "pace": pace,
            "calories": str(int(summary_dto.get('calories', 0))) if summary_dto.get('calories') else "",
            "averageHeartRate": f"{int(summary_dto.get('averageHR', 0))} bpm" if summary_dto.get('averageHR') else "",
            "weather": self.get_weather_data(garmin_activity),
            "laps": self.get_lap_data(garmin_activity)
        }
        
        # Add proper start and end times for JSON-LD schema
        if start_time_iso:
            strava_format["startTime"] = start_time_iso
        if end_time_iso:
            strava_format["endTime"] = end_time_iso
        
        # Add running dynamics directly from summaryDTO (this is the enhanced data we were missing!)
        running_dynamics = {}
        
        if summary_dto.get('averageRunCadence'):
            running_dynamics["avgCadence"] = f"{int(summary_dto['averageRunCadence'])} spm"
        
        if summary_dto.get('strideLength'):
            # Convert from meters to more readable format
            stride_m = summary_dto['strideLength']
            running_dynamics["avgStrideLength"] = f"{stride_m:.2f} m"
        
        if summary_dto.get('groundContactTime'):
            # Convert from seconds to milliseconds
            gct_ms = int(summary_dto['groundContactTime'] * 1000)
            running_dynamics["groundContactTime"] = f"{gct_ms} ms"
        
        if summary_dto.get('verticalOscillation'):
            # Convert from meters to centimeters
            vo_cm = summary_dto['verticalOscillation'] * 100
            running_dynamics["verticalOscillation"] = f"{vo_cm:.1f} cm"
        
        if summary_dto.get('averagePower'):
            running_dynamics["avgPower"] = f"{int(summary_dto['averagePower'])} W"
        
        if running_dynamics:
            strava_format["runningDynamics"] = running_dynamics
        
        # Add enhanced data if available (from FIT file parsing, when we get that working)
        if enhanced_data:
            if enhanced_data.get("runningDynamics"):
                # Merge with existing running dynamics
                if "runningDynamics" not in strava_format:
                    strava_format["runningDynamics"] = {}
                strava_format["runningDynamics"].update(enhanced_data["runningDynamics"])
        
        return strava_format

    def get_weather_data(self, activity: Dict) -> Dict:
        """Extract weather data from Garmin activity"""
        weather = {}
        
        # Garmin often has weather data in the activity
        if activity.get('weather'):
            weather_data = activity['weather']
            weather = {
                "description": weather_data.get('weatherCondition', ''),
                "temperature": f"{weather_data.get('temp', '')} ℉" if weather_data.get('temp') else "",
                "humidity": f"{weather_data.get('relativeHumidity', '')}%" if weather_data.get('relativeHumidity') else "",
                "windSpeed": f"{weather_data.get('windSpeed', '')} mi/h" if weather_data.get('windSpeed') else "",
                "windDirection": weather_data.get('windDirection', '')
            }
        
        return weather

    def get_lap_data(self, activity: Dict) -> List[Dict]:
        """Extract lap data from Garmin activity (basic version)"""
        # For now, return empty list - this would need activity details API call
        # to get lap information, which we can implement if needed
        return []

    def process_activities(self, specific_activity_id: Optional[str] = None) -> List[Dict]:
        """Main processing function with proper date filtering"""
        
        if not self.authenticate():
            return []
        
        if specific_activity_id:
            # Process single activity
            logger.info(f"Processing specific activity: {specific_activity_id}")
            try:
                activity = garth.connectapi(f"/activity-service/activity/{specific_activity_id}")
                if activity:
                    converted = self.convert_garmin_to_strava_format(activity)
                    return [converted]
            except Exception as e:
                logger.error(f"Error processing activity {specific_activity_id}: {e}")
            return []
        
        # Use the proper date filtering logic from get_activities_since_date
        try:
            activities_response = garth.connectapi("/activitylist-service/activities/search/activities", params={"limit": 100})
            all_activities = activities_response if isinstance(activities_response, list) else []
        except Exception as e:
            logger.error(f"Error fetching activities: {e}")
            return []
        
        # Apply proper date filtering logic
        processed_activities = []
        last_processed = self.get_last_processed()
        
        logger.info(f"Last processed info: {last_processed}")
        logger.info(f"Retrieved {len(all_activities)} activities from Garmin")
        
        for activity in all_activities:
            try:
                activity_id = activity.get('activityId')
                
                # Extract date more robustly from different timestamp formats
                start_time = activity.get('startTimeLocal', '')
                if 'T' in start_time:
                    activity_date = start_time.split('T')[0]
                elif ' ' in start_time:
                    activity_date = start_time.split(' ')[0]
                else:
                    activity_date = start_time
                
                logger.info(f"Evaluating activity {activity_id} from {activity_date}")
                
                # Apply the same filtering logic as get_activities_since_date
                should_process = False
                
                if last_processed.get("transition_mode"):
                    # Transition mode: Use date-based filtering only, ignore ID comparison
                    if activity_date and self.is_activity_newer(activity_date, last_processed["date"]):
                        should_process = True
                        logger.info(f"Will process activity {activity_id} (transition mode - newer than {last_processed['date']})")
                    else:
                        logger.info(f"Skipping activity {activity_id} (not newer than last Strava date {last_processed['date']})")
                else:
                    # Normal mode: Check Garmin ID comparison
                    if last_processed["id"] and str(activity_id) == last_processed["id"]:
                        logger.info(f"Found last processed Garmin activity {activity_id}. Stopping.")
                        break
                    elif activity_date and self.is_activity_newer(activity_date, last_processed["date"]):
                        should_process = True
                        logger.info(f"Will process activity {activity_id} (normal mode)")
                    else:
                        logger.info(f"Skipping activity {activity_id} (already processed)")
                
                if not should_process:
                    continue
                
                # Get detailed activity data
                try:
                    detailed_activity = garth.connectapi(f"/activity-service/activity/{activity_id}")
                    if not detailed_activity:
                        logger.warning(f"Could not get detailed data for activity {activity_id}")
                        detailed_activity = activity
                except Exception as e:
                    logger.warning(f"Error getting detailed activity data for {activity_id}: {e}")
                    detailed_activity = activity
                
                # Convert to Strava format
                converted = self.convert_garmin_to_strava_format(detailed_activity)
                
                # Temporarily disable FIT file download until we resolve API issues
                # logger.info(f"Downloading FIT file for activity {activity_id}")
                # fit_data = self.download_fit_file(activity_id)
                # if fit_data:
                #     enhanced = self.parse_fit_file(fit_data)
                #     if enhanced.get("runningDynamics"):
                #         converted["runningDynamics"] = enhanced["runningDynamics"]
                #         logger.info(f"Added running dynamics for activity {activity_id}")
                
                # Get sleep and wellness data for the activity date
                if activity_date:
                    logger.info(f"Getting sleep data for {activity_date}")
                    sleep_data = self.get_sleep_data(activity_date)
                    if sleep_data:
                        converted["sleepData"] = sleep_data
                        logger.info(f"Added sleep data for {activity_date}")
                    
                    logger.info(f"Getting wellness data for {activity_date}")
                    wellness_data = self.get_wellness_data(activity_date)
                    if wellness_data:
                        converted["wellness"] = wellness_data
                        logger.info(f"Added wellness data for {activity_date}")
                
                logger.info(f"Successfully processed activity {activity_id} with enhanced data")
                processed_activities.append(converted)
                
            except Exception as e:
                logger.error(f"Error processing activity {activity.get('activityId')}: {e}")
                continue
        
        logger.info(f"Processed {len(processed_activities)} activities total")
        return processed_activities

    def save_activities(self, activities: List[Dict]):
        """Save processed activities to JSON file"""
        try:
            with open(self.activities_output, 'w') as f:
                json.dump(activities, f, indent=2)
            logger.info(f"Saved {len(activities)} activities to {self.activities_output}")
        except Exception as e:
            logger.error(f"Error saving activities: {e}")

def main():
    """Main entry point"""
    try:
        scraper = GarminScraper()
        
        # Check for specific activity ID from command line
        specific_activity_id = sys.argv[1] if len(sys.argv) > 1 else None
        
        activities = scraper.process_activities(specific_activity_id)
        
        if activities:
            scraper.save_activities(activities)
            logger.info(f"Successfully processed {len(activities)} activities")
        else:
            logger.info("No new activities to process")
            # Still create empty activities.json for consistency
            scraper.save_activities([])
            
    except KeyboardInterrupt:
        logger.info("Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 