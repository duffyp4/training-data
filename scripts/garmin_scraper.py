#!/usr/bin/env python3
"""
Garmin Connect Scraper
Retrieves activity and wellness data from Garmin Connect using hybrid approach:
- REST API for daily wellness metrics (sleep, steps, body battery, resting HR)
- FIT file parsing for rich workout data (training effects, HR zones, running dynamics, location)
"""

import json
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import io

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
                    
                    return {
                        "id": last_id,
                        "date": last_date
                    }
        except Exception as e:
            logger.warning(f"Could not read last_id.json: {e}")
        
        return {"id": None, "date": None}

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
            
            # Parse last date format - handle Garmin timestamp formats
            if 'T' in last_date or (' ' in last_date and ':' in last_date):
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
            # Default to excluding the activity when date parsing fails (safer)
            return False

    def download_fit_file(self, activity_id: int) -> Optional[bytes]:
        """Download FIT file for an activity"""
        try:
            # Use garth's session to maintain authentication
            response = requests.get(
                f"https://connectapi.garmin.com/download-service/files/activity/{activity_id}",
                headers=garth.client.request_headers(),
                cookies=garth.client.session.cookies
            )
            
            if response.status_code == 200 and response.content:
                logger.info(f"Successfully downloaded FIT file for activity {activity_id} ({len(response.content)} bytes)")
                return response.content
            else:
                logger.warning(f"Failed to download FIT file for activity {activity_id}: {response.status_code}")
                return None
        except Exception as e:
            logger.warning(f"Could not download FIT file for activity {activity_id}: {e}")
            return None

    def get_city_from_coordinates(self, lat: float, lon: float) -> str:
        """Get city name from coordinates - simplified for now"""
        try:
            # For now, return a simple location based on known coordinates
            # In the future, this could use a geocoding service
            if abs(lat - 41.91) < 0.1 and abs(lon - (-87.68)) < 0.1:
                return "Chicago, IL"
            else:
                return f"Location: {lat:.2f}°N, {lon:.2f}°W"
        except Exception:
            return "Unknown Location"

    def parse_fit_file(self, fit_data: bytes) -> Dict[str, Any]:
        """Parse FIT file to extract comprehensive workout metrics"""
        enhanced_data = {
            "training_effects": {},
            "heart_rate_zones": {},
            "workout_summary": {},
            "running_dynamics": {},
            "location": None,
            "splits": []
        }
        
        try:
            fitfile = FitFile(io.BytesIO(fit_data))
            
            # 1. SESSION DATA (overall workout summary)
            for record in fitfile.get_messages('session'):
                for field in record:
                    if field.name == 'total_training_effect':
                        enhanced_data["training_effects"]["aerobic"] = field.value / 10  # Garmin stores as integer * 10
                    elif field.name == 'total_anaerobic_training_effect':
                        enhanced_data["training_effects"]["anaerobic"] = field.value / 10
                    elif field.name == 'avg_heart_rate':
                        enhanced_data["workout_summary"]["avg_hr"] = field.value
                    elif field.name == 'max_heart_rate':
                        enhanced_data["workout_summary"]["max_hr"] = field.value
                    elif field.name == 'avg_power':
                        enhanced_data["running_dynamics"]["avg_power"] = field.value
                    elif field.name == 'avg_running_cadence':
                        enhanced_data["running_dynamics"]["avg_cadence"] = field.value
                    elif field.name in ['start_position_lat', 'start_position_long']:
                        # Convert from Garmin semicircles to degrees
                        if field.name == 'start_position_lat':
                            lat = field.value * (180 / (2**31))
                            enhanced_data["location"] = {"lat": lat}
                        elif field.name == 'start_position_long':
                            lon = field.value * (180 / (2**31))
                            if enhanced_data.get("location"):
                                enhanced_data["location"]["lon"] = lon
                break  # Only need first session record
            
            # Convert location to city name
            if enhanced_data["location"] and enhanced_data["location"].get("lat") and enhanced_data["location"].get("lon"):
                city = self.get_city_from_coordinates(enhanced_data["location"]["lat"], enhanced_data["location"]["lon"])
                enhanced_data["location"] = city
            
            # 2. LAP DATA (per-split running dynamics)
            for lap_record in fitfile.get_messages('lap'):
                lap_data = {}
                for field in lap_record:
                    if field.name == 'avg_heart_rate':
                        lap_data["avg_hr"] = field.value
                    elif field.name == 'max_heart_rate':
                        lap_data["max_hr"] = field.value
                    elif field.name == 'avg_running_cadence':
                        lap_data["avg_cadence"] = f"{field.value} spm" if field.value else None
                    elif field.name == 'avg_step_length':
                        # Convert from mm to meters
                        lap_data["avg_stride_length"] = f"{field.value / 1000:.2f} m" if field.value else None
                    elif field.name == 'avg_stance_time':
                        # Convert to milliseconds
                        lap_data["ground_contact_time"] = f"{field.value:.0f} ms" if field.value else None
                    elif field.name == 'avg_vertical_oscillation':
                        # Convert from mm to cm
                        lap_data["vertical_oscillation"] = f"{field.value / 10:.1f} cm" if field.value else None
                
                if lap_data:
                    enhanced_data["splits"].append(lap_data)
            
            # 3. HEART RATE ZONE CALCULATION (sample from record data)
            hr_readings = []
            record_count = 0
            
            for record in fitfile.get_messages('record'):
                record_count += 1
                for field in record:
                    if field.name == 'heart_rate' and field.value:
                        hr_readings.append(field.value)
                
                # Sample every 10th record for efficiency
                if record_count % 10 != 0:
                    continue
                    
                # Stop if we have enough data points (200+ samples is plenty for zones)
                if len(hr_readings) >= 200:
                    break
            
            # Calculate time in zones from sampled HR data
            if hr_readings:
                enhanced_data["heart_rate_zones"] = self.calculate_hr_zones(hr_readings)
            
            logger.info(f"Successfully parsed FIT file: {len(hr_readings)} HR samples, {len(enhanced_data['splits'])} laps")
            
        except Exception as e:
            logger.warning(f"Error parsing FIT file: {e}")
        
        return enhanced_data

    def calculate_hr_zones(self, hr_readings: List[int], max_hr: int = 193) -> Dict:
        """Calculate time in HR zones from sampled readings"""
        zones = {f"zone_{i}": 0 for i in range(1, 6)}
        
        for hr in hr_readings:
            hr_percent = (hr / max_hr) * 100
            if hr_percent < 60:
                zones["zone_1"] += 1
            elif hr_percent < 70:
                zones["zone_2"] += 1
            elif hr_percent < 80:
                zones["zone_3"] += 1
            elif hr_percent < 90:
                zones["zone_4"] += 1
            else:
                zones["zone_5"] += 1
        
        # Convert counts to time estimates (assuming samples represent equal time intervals)
        total_samples = sum(zones.values())
        if total_samples > 0:
            # Estimate total workout time from HR data points (rough approximation)
            estimated_total_seconds = total_samples * 10  # Assuming ~10 second intervals
            for zone in zones:
                zone_percentage = zones[zone] / total_samples
                zone_seconds = int(estimated_total_seconds * zone_percentage)
                if zone_seconds > 0:
                    minutes = zone_seconds // 60
                    seconds = zone_seconds % 60
                    zones[zone] = f"{minutes}:{seconds:02d}"
                else:
                    zones[zone] = "0:00"
        
        return zones

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
        """Get wellness data for a specific date (removed self-evaluation)"""
        try:
            wellness = {}
            
            # Get daily step data
            try:
                steps_data = garth.connectapi(f"/wellness-service/wellness/dailySummaryChart/{date}")
                if steps_data and steps_data.get('summaryList'):
                    for summary in steps_data['summaryList']:
                        if summary.get('summaryId') == 'steps':
                            wellness["dailySteps"] = summary.get('value', 0)
                            break
                # Fallback to user summary endpoint
                if 'dailySteps' not in wellness:
                    user_summary = garth.connectapi(f"/usersummary-service/usersummary/daily/{date}")
                    if user_summary and user_summary.get('totalSteps'):
                        wellness["dailySteps"] = user_summary['totalSteps']
            except Exception as e:
                logger.debug(f"Could not get step data: {e}")
            
            # Get body battery data
            try:
                bb_data = garth.connectapi(f"/wellness-service/wellness/bodyBattery/reports/daily/{date}")
                if bb_data and bb_data.get('bodyBatteryValuesArray'):
                    # Calculate charge and drain from the battery values
                    values = bb_data['bodyBatteryValuesArray']
                    if values:
                        first_val = values[0].get('charged', 0)
                        last_val = values[-1].get('charged', 0)
                        if last_val > first_val:
                            wellness["bodyBattery"] = {
                                "charge": last_val - first_val,
                                "drain": 0
                            }
                        else:
                            wellness["bodyBattery"] = {
                                "charge": 0,
                                "drain": first_val - last_val
                            }
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
                    wellness["restingHeartRate"] = rhr_data['restingHeartRate']
            except Exception as e:
                logger.debug(f"Could not get resting heart rate: {e}")
            
            # Get HRV data
            try:
                hrv_data = garth.connectapi(f"/hrv-service/hrv/{date}")
                if hrv_data and hrv_data.get('hrvSummary', {}).get('weeklyAvg'):
                    wellness["hrv"] = hrv_data['hrvSummary']['weeklyAvg']
            except Exception as e:
                logger.debug(f"Could not get HRV data: {e}")

            # Note: Removed self-evaluation data collection per user request
            
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

    def convert_garmin_to_activity_format(self, garmin_activity: Dict, fit_data: Optional[Dict] = None) -> Dict:
        """Convert Garmin activity format to standardized activity format with FIT enhancement"""
        
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
                    # ISO format: "2025-07-07T14:29:18.000" or "2025-07-07T14:29:18"
                    # Clean up the timestamp and ensure proper format
                    clean_time = start_time_local.split('+')[0]  # Remove timezone offset if present
                    
                    # Ensure it ends with .000Z for consistency
                    if not clean_time.endswith('.000'):
                        if '.' in clean_time:
                            # Has milliseconds already, just ensure 3 digits
                            parts = clean_time.split('.')
                            ms = parts[1][:3].ljust(3, '0')  # Take first 3 digits, pad if needed
                            clean_time = f"{parts[0]}.{ms}"
                        else:
                            # No milliseconds, add .000
                            clean_time += '.000'
                    
                    start_time_iso = clean_time + 'Z'
                    
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

        # Use FIT data when available, otherwise fall back to API data
        if fit_data and fit_data.get("workout_summary"):
            # Prefer FIT file data for basic metrics
            distance_m = summary_dto.get('distance', 0)
            distance_mi = round(distance_m * 0.000621371, 2) if distance_m else 0
            
            # Convert duration from seconds to MM:SS format  
            duration_s = summary_dto.get('duration', 0)
            if duration_s:
                duration_s = int(float(duration_s))
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
            
            # Use FIT file HR data
            avg_hr = fit_data["workout_summary"].get("avg_hr", summary_dto.get('averageHR', 0))
            max_hr = fit_data["workout_summary"].get("max_hr", summary_dto.get('maxHR', 0))
        else:
            # Fallback to API data when FIT parsing fails
            distance_m = summary_dto.get('distance', 0)
            distance_mi = round(distance_m * 0.000621371, 2) if distance_m else 0
            
            duration_s = summary_dto.get('duration', 0)
            if duration_s:
                duration_s = int(float(duration_s))
                minutes = duration_s // 60
                seconds = duration_s % 60
                duration_formatted = f"{minutes}:{seconds:02d}"
            else:
                duration_formatted = ""
            
            pace = ""
            if distance_mi > 0 and duration_s > 0:
                pace_s_per_mile = duration_s / distance_mi
                pace_min = int(pace_s_per_mile // 60)
                pace_sec = int(pace_s_per_mile % 60)
                pace = f"{pace_min}:{pace_sec:02d}/mi"

            elevation_m = summary_dto.get('elevationGain', 0)
            elevation_ft = int(round(elevation_m * 3.28084)) if elevation_m else 0
            
            avg_hr = summary_dto.get('averageHR', 0)
            max_hr = summary_dto.get('maxHR', 0)
        
        # Get activity type from activityTypeDTO
        type_key = activity_type_dto.get('typeKey', 'unknown')
        
        # Convert activity type to standard format
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
        
        # Base activity data in standard format
        activity_format = {
            "activityId": str(garmin_activity.get('activityId', '')),
            "sport": exercise_type,
            "date": formatted_date,
            "workoutName": workout_name,
            "duration": duration_formatted,
            "distance": f"{distance_mi:.2f} mi" if distance_mi else "",
            "elevation": f"{elevation_ft} ft",
            "pace": pace,
            "calories": str(int(summary_dto.get('calories', 0))) if summary_dto.get('calories') else "",
            "averageHeartRate": f"{int(avg_hr)} bpm" if avg_hr else "",
            "maxHeartRate": f"{int(max_hr)} bpm" if max_hr else "",
            "weather": self.get_weather_data(garmin_activity),
            "laps": self.get_lap_data(garmin_activity)
        }
        
        # Add proper start and end times for JSON-LD schema
        if start_time_iso:
            activity_format["startTime"] = start_time_iso
        if end_time_iso:
            activity_format["endTime"] = end_time_iso
        
        # Add FIT file data if available
        if fit_data:
            if fit_data.get("training_effects"):
                activity_format["trainingEffects"] = fit_data["training_effects"]
            
            if fit_data.get("heart_rate_zones"):
                activity_format["timeInHRZones"] = fit_data["heart_rate_zones"]
                
            if fit_data.get("location"):
                activity_format["location"] = fit_data["location"]
                
            if fit_data.get("splits"):
                # Merge FIT split data with API lap data
                for i, fit_split in enumerate(fit_data["splits"]):
                    if i < len(activity_format["laps"]):
                        activity_format["laps"][i]["runningDynamics"] = fit_split
        
        return activity_format

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
        """Extract lap data from Garmin activity using splits endpoint"""
        activity_id = activity.get('activityId')
        if not activity_id:
            return []
        
        try:
            # Use the splits endpoint to get detailed lap data
            splits_data = garth.connectapi(f"/activity-service/activity/{activity_id}/splits")
            
            if not splits_data or not isinstance(splits_data, dict):
                logger.debug(f"No splits data found for activity {activity_id}")
                return []
            
            # Extract lap information from the splits response
            laps = []
            splits_list = splits_data.get('lapDTOs', [])
            
            for i, split in enumerate(splits_list):
                # Convert duration from seconds to MM:SS format
                duration_s = split.get('movingDuration', split.get('duration', 0))
                time_str = ""
                if duration_s:
                    try:
                        duration_s = int(float(duration_s))
                        minutes = duration_s // 60
                        seconds = duration_s % 60
                        time_str = f"{minutes}:{seconds:02d}"
                    except (ValueError, TypeError):
                        pass
                
                lap_data = {
                    "lapNumber": i + 1,
                    "distance": "",
                    "time": time_str,
                    "pace": "",  # Will be calculated below
                    "elevation": "",
                    "heartRate": f"{int(split.get('averageHR', 0))} bpm" if split.get('averageHR') else "",
                    "stepType": None  # Will be set from FIT data if available
                }
                
                # Convert pace from speed if available
                if split.get('averageSpeed'):
                    try:
                        speed_mps = float(split['averageSpeed'])
                        # Convert m/s to pace (min/mile)
                        if speed_mps > 0:
                            pace_s_per_mile = 1609.34 / speed_mps  # meters per mile / speed
                            pace_min = int(pace_s_per_mile // 60)
                            pace_sec = int(pace_s_per_mile % 60)
                            lap_data["pace"] = f"{pace_min}:{pace_sec:02d} /mi"
                    except (ValueError, TypeError):
                        pass
                
                # Convert distance from meters to miles
                if split.get('distance'):
                    try:
                        distance_m = float(split['distance'])
                        distance_mi = distance_m * 0.000621371
                        lap_data["distance"] = f"{distance_mi:.2f} mi"
                    except (ValueError, TypeError):
                        pass
                
                # Convert elevation from meters to feet
                if split.get('elevationGain'):
                    try:
                        elev_m = float(split['elevationGain'])
                        elev_ft = int(elev_m * 3.28084)
                        lap_data["elevation"] = f"{elev_ft} ft"
                    except (ValueError, TypeError):
                        pass
                
                laps.append(lap_data)
            
            if laps:
                logger.info(f"Successfully extracted {len(laps)} laps for activity {activity_id}")
            else:
                logger.debug(f"No lap data available for activity {activity_id}")
            
            return laps
            
        except Exception as e:
            logger.warning(f"Could not fetch lap data for activity {activity_id}: {e}")
            return []

    def process_activities(self, specific_activity_id: Optional[str] = None) -> List[Dict]:
        """Main processing function with FIT file parsing"""
        
        if not self.authenticate():
            return []
        
        if specific_activity_id:
            # Process single activity
            logger.info(f"Processing specific activity: {specific_activity_id}")
            try:
                activity = garth.connectapi(f"/activity-service/activity/{specific_activity_id}")
                if activity:
                    converted = self.convert_garmin_to_activity_format(activity)
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
                        logger.info(f"Skipping activity {activity_id} (not newer than last processed date {last_processed['date']})")
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
                
                # Download and parse FIT file for enhanced workout data
                fit_data = None
                logger.info(f"Downloading FIT file for activity {activity_id}")
                fit_bytes = self.download_fit_file(activity_id)
                if fit_bytes:
                    fit_data = self.parse_fit_file(fit_bytes)
                    logger.info(f"Successfully parsed FIT file for activity {activity_id}")
                else:
                    logger.warning(f"Could not download FIT file for activity {activity_id}, using API data only")
                
                # Convert to standard activity format with FIT enhancement
                converted = self.convert_garmin_to_activity_format(detailed_activity, fit_data)
                
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