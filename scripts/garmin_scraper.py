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
            # Parse Garmin date format (YYYY-MM-DD)
            activity_dt = datetime.strptime(activity_date, "%Y-%m-%d")
            
            # Parse last date format (e.g., "Tue, 7/1/2025")
            if ',' in last_date:
                date_part = last_date.split(',')[1].strip()
                last_dt = datetime.strptime(date_part, "%m/%d/%Y")
            else:
                # Fallback for different date formats
                last_dt = datetime.strptime(last_date, "%Y-%m-%d")
            
            return activity_dt > last_dt
        except Exception as e:
            logger.warning(f"Could not parse dates for comparison: activity='{activity_date}', last='{last_date}': {e}")
            return True

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
            return self.client.download_activity(activity_id, dl_fmt=self.client.ActivityDownloadFormat.ORIGINAL)
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
            fit_file = FitFile(fit_data)
            
            # Track all record messages for detailed analysis
            records = []
            for record in fit_file.get_messages('record'):
                record_data = {}
                for field in record:
                    record_data[field.name] = field.value
                records.append(record_data)
            
            if records:
                # Extract running dynamics
                cadence_values = [r.get('cadence') for r in records if r.get('cadence')]
                if cadence_values:
                    enhanced_data["runningDynamics"]["avgCadence"] = sum(cadence_values) // len(cadence_values)
                
                # Extract stride length if available
                stride_length_values = [r.get('stride_length') for r in records if r.get('stride_length')]
                if stride_length_values:
                    enhanced_data["runningDynamics"]["avgStrideLength"] = round(sum(stride_length_values) / len(stride_length_values), 2)
                
                # Extract ground contact time
                gct_values = [r.get('stance_time') for r in records if r.get('stance_time')]
                if gct_values:
                    enhanced_data["runningDynamics"]["groundContactTime"] = sum(gct_values) // len(gct_values)
                
                # Extract vertical oscillation
                vo_values = [r.get('vertical_oscillation') for r in records if r.get('vertical_oscillation')]
                if vo_values:
                    enhanced_data["runningDynamics"]["verticalOscillation"] = round(sum(vo_values) / len(vo_values), 1)
            
        except Exception as e:
            logger.warning(f"Error parsing FIT file: {e}")
        
        return enhanced_data

    def get_sleep_data(self, date: str) -> Optional[Dict]:
        """Get sleep data for a specific date"""
        try:
            sleep_data = self.client.get_sleep_data(date)
            if sleep_data:
                return {
                    "sleepScore": sleep_data.get('sleepScores', {}).get('overall', {}).get('value'),
                    "deepSleep": self.format_sleep_duration(sleep_data.get('deepSleepSeconds')),
                    "lightSleep": self.format_sleep_duration(sleep_data.get('lightSleepSeconds')),
                    "remSleep": self.format_sleep_duration(sleep_data.get('remSleepSeconds')),
                    "awakeTime": self.format_sleep_duration(sleep_data.get('awakeDurationSeconds'))
                }
        except Exception as e:
            logger.warning(f"Could not fetch sleep data for {date}: {e}")
        return None

    def get_wellness_data(self, date: str) -> Optional[Dict]:
        """Get wellness data for a specific date"""
        try:
            # Get body battery data
            body_battery = self.client.get_body_battery(date)
            
            # Get HRV data
            hrv_data = self.client.get_hrv_data(date)
            
            # Get resting heart rate
            rhr_data = self.client.get_rhr_day(date)
            
            wellness = {}
            
            if body_battery:
                wellness["bodyBattery"] = body_battery.get('charged')
            
            if hrv_data and hrv_data.get('hrvSummary'):
                wellness["hrv"] = hrv_data['hrvSummary'].get('weeklyAvg')
            
            if rhr_data:
                wellness["restingHeartRate"] = rhr_data.get('restingHeartRate')
            
            return wellness if wellness else None
            
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
        
        # Parse the start time
        start_time_local = garmin_activity.get('startTimeLocal', '')
        start_date = start_time_local.split('T')[0] if start_time_local else ''
        
        # Format date to match existing format (e.g., "Tue, 7/1/2025")
        formatted_date = ""
        if start_date:
            try:
                dt = datetime.strptime(start_date, "%Y-%m-%d")
                formatted_date = dt.strftime("%a, %-m/%-d/%Y")
            except:
                formatted_date = start_date

        # Convert distance from meters to miles
        distance_m = garmin_activity.get('distance', 0)
        distance_mi = round(distance_m * 0.000621371, 2) if distance_m else 0
        
        # Convert duration from seconds to MM:SS format
        duration_s = garmin_activity.get('duration', 0)
        duration_formatted = f"{duration_s // 60}:{duration_s % 60:02d}" if duration_s else ""
        
        # Calculate pace (min/mile)
        pace = ""
        if distance_mi > 0 and duration_s > 0:
            pace_s_per_mile = duration_s / distance_mi
            pace_min = int(pace_s_per_mile // 60)
            pace_sec = int(pace_s_per_mile % 60)
            pace = f"{pace_min}:{pace_sec:02d}/mi"

        # Convert elevation from meters to feet
        elevation_m = garmin_activity.get('elevationGain', 0)
        elevation_ft = round(elevation_m * 3.28084) if elevation_m else 0
        
        # Get activity type
        activity_type = garmin_activity.get('activityType', {}).get('typeKey', 'unknown')
        
        # Convert activity type to match Strava format
        exercise_type = "Run" if "running" in activity_type.lower() else activity_type.title()
        
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
            "calories": str(garmin_activity.get('calories', '')),
            "averageHeartRate": f"{garmin_activity.get('averageHR', '')} bpm" if garmin_activity.get('averageHR') else "",
            "weather": self.get_weather_data(garmin_activity),
            "laps": self.get_lap_data(garmin_activity)
        }
        
        # Add enhanced data if available
        if enhanced_data:
            if enhanced_data.get("runningDynamics"):
                strava_format["runningDynamics"] = enhanced_data["runningDynamics"]
        
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
        """Main processing function"""
        
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
        
        # Process new activities  
        try:
            activities_response = garth.connectapi("/activitylist-service/activities/search/activities", params={"limit": 50})
            activities = activities_response if isinstance(activities_response, list) else []
        except Exception as e:
            logger.error(f"Error fetching activities: {e}")
            return []
        
        processed_activities = []
        last_processed = self.get_last_processed()
        
        for activity in activities:
            try:
                logger.info(f"Processing activity {activity.get('activityId')}")
                
                # Convert to Strava format
                converted = self.convert_garmin_to_strava_format(activity)
                
                # For initial testing, skip enhanced data collection
                logger.info(f"Successfully converted activity {activity.get('activityId')}")
                
                processed_activities.append(converted)
                
            except Exception as e:
                logger.error(f"Error processing activity {activity.get('activityId')}: {e}")
                continue
        
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