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
                                       num_splits: int,
                                       location: Optional[str] = None) -> List[float]:
        """
        Interpolate temperatures for workout splits using historical weather data
        """
        if not location:
            location = self.default_location
        
        try:
            # Parse workout times
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
            
            # Try Visual Crossing first (recommended)
            weather_data = self.get_historical_weather_visual_crossing(location, start_dt, end_dt)
            
            if weather_data:
                return self._interpolate_from_hourly_data(weather_data, start_dt, end_dt, num_splits)
            
            # Fallback to OpenWeatherMap
            lat, lon = map(float, location.split(','))
            start_weather = self.get_historical_weather_openweather(lat, lon, int(start_dt.timestamp()))
            end_weather = self.get_historical_weather_openweather(lat, lon, int(end_dt.timestamp()))
            
            if start_weather and end_weather:
                return self._linear_interpolate(
                    start_weather['temp'], 
                    end_weather['temp'], 
                    num_splits
                )
            
            # Final fallback - realistic estimates based on time of day
            return self._estimate_temperatures_by_time(start_dt, end_dt, num_splits)
            
        except Exception as e:
            logger.error(f"Error interpolating temperatures: {e}")
            return self._estimate_temperatures_by_time(None, None, num_splits)
    
    def _interpolate_from_hourly_data(self, 
                                    weather_data: List[dict], 
                                    start_dt: datetime, 
                                    end_dt: datetime, 
                                    num_splits: int) -> List[float]:
        """
        Interpolate temperatures from hourly weather data
        """
        # Find temperature at start and end times
        start_temp = self._find_temperature_at_time(weather_data, start_dt)
        end_temp = self._find_temperature_at_time(weather_data, end_dt)
        
        return self._linear_interpolate(start_temp, end_temp, num_splits)
    
    def _find_temperature_at_time(self, weather_data: List[dict], target_time: datetime) -> float:
        """
        Find temperature at specific time from hourly data
        """
        target_hour = target_time.strftime('%H:00:00')
        target_date = target_time.strftime('%Y-%m-%d')
        
        # Look for exact hour match
        for record in weather_data:
            if record.get('date') == target_date and record.get('datetime') == target_hour:
                return record.get('temp', 70.0)
        
        # Fallback to nearest hour
        closest_temp = 70.0
        min_diff = float('inf')
        
        for record in weather_data:
            if record.get('date') == target_date:
                record_time = datetime.strptime(f"{target_date} {record['datetime']}", '%Y-%m-%d %H:%M:%S')
                diff = abs((target_time - record_time).total_seconds())
                if diff < min_diff:
                    min_diff = diff
                    closest_temp = record.get('temp', 70.0)
        
        return closest_temp
    
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
def get_split_temperatures(activity_data: dict, num_splits: int) -> List[float]:
    """
    Convenience function to get split temperatures for an activity
    """
    interpolator = WeatherInterpolator()
    
    start_time = activity_data.get('startTime', '')
    end_time = activity_data.get('endTime', '')
    location = interpolator.extract_gps_location(activity_data)
    
    return interpolator.interpolate_workout_temperatures(start_time, end_time, num_splits, location)

if __name__ == "__main__":
    # Test the weather interpolation
    test_activity = {
        'startTime': '2025-07-07T08:08:43.000Z',
        'endTime': '2025-07-07T09:35:26.000Z'
    }
    
    temps = get_split_temperatures(test_activity, 6)
    print(f"Split temperatures: {temps}") 