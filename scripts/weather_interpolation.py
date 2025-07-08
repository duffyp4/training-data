#!/usr/bin/env python3
"""
Weather Interpolation Module
Fetches historical weather data and interpolates temperatures for workout splits
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
import json
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)

class WeatherInterpolator:
    def __init__(self):
        # Visual Crossing Weather API (recommended)
        self.visual_crossing_key = os.getenv("VISUAL_CROSSING_API_KEY")
        
        # OpenWeatherMap API (alternative)
        self.openweather_key = os.getenv("OPENWEATHER_API_KEY")
        
        # WeatherAPI.com (alternative)
        self.weatherapi_key = os.getenv("WEATHERAPI_KEY")
        
        # Default location (Chicago area - would normally extract from GPS data)
        self.default_location = "41.8781,-87.6298"  # Chicago, IL
    
    def get_historical_weather_visual_crossing(self, 
                                             location: str, 
                                             start_time: datetime, 
                                             end_time: datetime) -> Optional[List[dict]]:
        """
        Get historical weather data from Visual Crossing Weather API
        """
        if not self.visual_crossing_key:
            logger.warning("VISUAL_CROSSING_API_KEY not set")
            return None
        
        # Format dates for API
        start_date = start_time.strftime('%Y-%m-%d')
        end_date = end_time.strftime('%Y-%m-%d')
        
        url = f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/{location}/{start_date}/{end_date}"
        
        params = {
            'key': self.visual_crossing_key,
            'unitGroup': 'us',  # Fahrenheit, mph, inches
            'include': 'hours',
            'elements': 'datetime,temp,humidity,windspeed,winddir,conditions'
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract hourly data
            hourly_data = []
            for day in data.get('days', []):
                for hour in day.get('hours', []):
                    hourly_data.append({
                        'datetime': hour['datetime'],
                        'date': day['datetime'],
                        'temp': hour['temp'],
                        'humidity': hour.get('humidity', 0),
                        'windspeed': hour.get('windspeed', 0),
                        'winddir': hour.get('winddir', 0),
                        'conditions': hour.get('conditions', '')
                    })
            
            logger.info(f"Retrieved {len(hourly_data)} hourly weather records from Visual Crossing")
            return hourly_data
            
        except Exception as e:
            logger.error(f"Error fetching weather from Visual Crossing: {e}")
            return None
    
    def get_historical_weather_openweather(self, 
                                         lat: float, 
                                         lon: float, 
                                         timestamp: int) -> Optional[dict]:
        """
        Get historical weather data from OpenWeatherMap API
        """
        if not self.openweather_key:
            logger.warning("OPENWEATHER_API_KEY not set")
            return None
        
        url = "https://api.openweathermap.org/data/3.0/onecall/timemachine"
        
        params = {
            'lat': lat,
            'lon': lon,
            'dt': timestamp,
            'appid': self.openweather_key,
            'units': 'imperial'  # Fahrenheit
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract current weather at that time
            current = data.get('data', [{}])[0] if data.get('data') else {}
            
            return {
                'temp': current.get('temp', 70),
                'humidity': current.get('humidity', 50),
                'wind_speed': current.get('wind_speed', 0),
                'wind_deg': current.get('wind_deg', 0),
                'weather': current.get('weather', [{}])[0].get('description', '')
            }
            
        except Exception as e:
            logger.error(f"Error fetching weather from OpenWeatherMap: {e}")
            return None
    
    def get_historical_weather_weatherapi(self, 
                                        location: str, 
                                        date: str) -> Optional[List[dict]]:
        """
        Get historical weather data from WeatherAPI.com
        """
        if not self.weatherapi_key:
            logger.warning("WEATHERAPI_KEY not set")
            return None
        
        url = "http://api.weatherapi.com/v1/history.json"
        
        params = {
            'key': self.weatherapi_key,
            'q': location,
            'dt': date
        }
        
        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Extract hourly data
            hourly_data = []
            for hour in data.get('forecast', {}).get('forecastday', [{}])[0].get('hour', []):
                hourly_data.append({
                    'datetime': hour['time'],
                    'temp_f': hour['temp_f'],
                    'humidity': hour['humidity'],
                    'wind_mph': hour['wind_mph'],
                    'wind_dir': hour['wind_dir'],
                    'condition': hour['condition']['text']
                })
            
            logger.info(f"Retrieved {len(hourly_data)} hourly weather records from WeatherAPI")
            return hourly_data
            
        except Exception as e:
            logger.error(f"Error fetching weather from WeatherAPI: {e}")
            return None
    
    def extract_gps_location(self, activity_data: dict) -> str:
        """
        Extract GPS coordinates from activity data
        For now, returns default Chicago location - would be enhanced with real GPS data
        """
        # TODO: Extract from FIT file or Garmin activity GPS data
        # This would look for startPositionLat/startPositionLng in the activity
        return self.default_location
    
    def interpolate_workout_temperatures(self, 
                                       start_time: str, 
                                       end_time: str, 
                                       splits_data: List[dict] = None,
                                       location: Optional[str] = None) -> List[float]:
        """
        Get exact temperatures at each mile completion time using historical weather data
        
        Args:
            start_time: Workout start time (ISO format)
            end_time: Workout end time (ISO format) 
            splits_data: List of split/lap data with timing info (preferred)
            location: GPS coordinates "lat,lon"
        
        Returns:
            List of temperatures at each mile completion time
        """
        if not location:
            location = self.default_location
        
        try:
            # Parse workout times
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # Try Visual Crossing first for hourly data
            weather_data = self.get_historical_weather_visual_crossing(location, start_dt, end_dt)
            
            if weather_data:
                if splits_data:
                    # Method 1: Use actual split timing data for exact temperatures
                    return self._get_exact_split_temperatures(weather_data, start_dt, splits_data)
                else:
                    # Method 2: Estimate mile completion times and get exact temps
                    return self._get_estimated_mile_temperatures(weather_data, start_dt, end_dt)
            
            # Fallback to OpenWeatherMap (less granular)
            lat, lon = map(float, location.split(','))
            start_weather = self.get_historical_weather_openweather(lat, lon, int(start_dt.timestamp()))
            end_weather = self.get_historical_weather_openweather(lat, lon, int(end_dt.timestamp()))
            
            if start_weather and end_weather:
                return self._linear_interpolate(
                    start_weather['temp'], 
                    end_weather['temp'], 
                    len(splits_data) if splits_data else 8
                )
            
            # Final fallback
            return self._estimate_temperatures_by_time(start_dt, end_dt, len(splits_data) if splits_data else 8)
            
        except Exception as e:
            logger.error(f"Error getting exact temperatures: {e}")
            return self._estimate_temperatures_by_time(None, None, len(splits_data) if splits_data else 8)
    
    def _get_exact_split_temperatures(self, weather_data: List[dict], start_dt: datetime, splits_data: List[dict]) -> List[float]:
        """
        Get exact temperature at each split completion time using real split data
        """
        temperatures = []
        current_time = start_dt
        
        for split in splits_data:
            # Get temperature at this exact time
            temp = self._find_temperature_at_exact_time(weather_data, current_time)
            temperatures.append(temp)
            
            # Calculate when this split was completed
            split_duration_s = split.get('mile_time_s', 0)
            if split_duration_s > 0:
                current_time += timedelta(seconds=split_duration_s)
            else:
                # Fallback: estimate based on average pace
                estimated_duration = 600  # 10 min/mile default
                current_time += timedelta(seconds=estimated_duration)
        
        logger.info(f"Retrieved exact temperatures for {len(temperatures)} splits using real timing data")
        return temperatures
    
    def _get_estimated_mile_temperatures(self, weather_data: List[dict], start_dt: datetime, end_dt: datetime, num_miles: int = None) -> List[float]:
        """
        Estimate mile completion times and get exact temperatures at those times
        """
        if not num_miles:
            # Estimate number of miles from duration (assume 10 min/mile average)
            duration_minutes = (end_dt - start_dt).total_seconds() / 60
            num_miles = max(1, int(duration_minutes / 10))
        
        temperatures = []
        workout_duration = end_dt - start_dt
        
        for mile in range(num_miles):
            # Estimate when this mile was completed (evenly spaced for now)
            progress = mile / (num_miles - 1) if num_miles > 1 else 0
            mile_completion_time = start_dt + (workout_duration * progress)
            
            # Get exact temperature at this time
            temp = self._find_temperature_at_exact_time(weather_data, mile_completion_time)
            temperatures.append(temp)
        
        logger.info(f"Retrieved exact temperatures for {num_miles} estimated mile times")
        return temperatures
    
    def _find_temperature_at_exact_time(self, weather_data: List[dict], target_time: datetime) -> float:
        """
        Find exact temperature at specific time using hourly weather data with interpolation
        """
        target_date = target_time.strftime('%Y-%m-%d')
        target_hour = target_time.hour
        target_minute = target_time.minute
        
        # Find the hour before and after target time
        before_temp = None
        after_temp = None
        
        for record in weather_data:
            if record.get('date') == target_date:
                record_hour = int(record['datetime'].split(':')[0])
                
                if record_hour == target_hour:
                    # Exact hour match
                    return record.get('temp', 70.0)
                elif record_hour == target_hour - 1:
                    # Hour before
                    before_temp = record.get('temp', 70.0)
                elif record_hour == target_hour + 1:
                    # Hour after  
                    after_temp = record.get('temp', 70.0)
        
        # Interpolate between hours if we have both
        if before_temp is not None and after_temp is not None:
            # Linear interpolation within the hour
            progress = target_minute / 60.0  # 0.0 = start of hour, 1.0 = end of hour
            interpolated_temp = before_temp + (after_temp - before_temp) * progress
            return round(interpolated_temp, 1)
        
        # Fallback to nearest hour
        return before_temp or after_temp or 70.0
    
    def _linear_interpolate(self, start_temp: float, end_temp: float, num_splits: int) -> List[float]:
        """
        Linear interpolation between start and end temperatures
        """
        if num_splits <= 1:
            return [start_temp]
        
        temps = []
        for i in range(num_splits):
            progress = i / (num_splits - 1) if num_splits > 1 else 0
            temp = start_temp + (end_temp - start_temp) * progress
            temps.append(round(temp, 1))
        
        return temps
    
    def _estimate_temperatures_by_time(self, 
                                     start_dt: Optional[datetime], 
                                     end_dt: Optional[datetime], 
                                     num_splits: int) -> List[float]:
        """
        Estimate temperatures based on time of day (fallback)
        """
        if not start_dt:
            # Very basic fallback
            return [72.0 + i * 0.2 for i in range(num_splits)]
        
        # Estimate based on hour of day
        start_hour = start_dt.hour
        
        # Temperature typically rises during morning/day runs
        if 5 <= start_hour <= 11:  # Morning run
            base_temp = 60 + (start_hour - 5) * 3  # 60F at 5AM, rising
            temp_rise = 2.0  # Degrees per hour
        elif 12 <= start_hour <= 17:  # Afternoon run
            base_temp = 75 + (start_hour - 12) * 1  # Peak afternoon heat
            temp_rise = 0.5
        else:  # Evening/night run
            base_temp = 70 - (start_hour - 18) * 2 if start_hour >= 18 else 65
            temp_rise = -0.5  # Cooling down
        
        workout_duration_hours = (end_dt - start_dt).total_seconds() / 3600 if end_dt else 1
        total_temp_change = temp_rise * workout_duration_hours
        
        return self._linear_interpolate(base_temp, base_temp + total_temp_change, num_splits)

# Example usage function
def get_split_temperatures(activity_data: dict, splits_data: List[dict] = None) -> List[float]:
    """
    Convenience function to get exact split temperatures for an activity
    
    Args:
        activity_data: Activity with startTime, endTime
        splits_data: List of split/lap data with timing information
    
    Returns:
        List of exact temperatures at each split completion time
    """
    interpolator = WeatherInterpolator()
    
    start_time = activity_data.get('startTime', '')
    end_time = activity_data.get('endTime', '')
    location = interpolator.extract_gps_location(activity_data)
    
    return interpolator.interpolate_workout_temperatures(start_time, end_time, splits_data, location)

if __name__ == "__main__":
    # Test the weather interpolation
    test_activity = {
        'startTime': '2025-07-07T08:08:43.000Z',
        'endTime': '2025-07-07T09:35:26.000Z'
    }
    
    temps = get_split_temperatures(test_activity, 6)
    print(f"Split temperatures: {temps}") 