#!/usr/bin/env python3
"""
Test script for weather API integration
"""

import os
from weather_interpolation import WeatherInterpolator

def test_weather_apis():
    """Test weather API integration with sample workout data"""
    
    # Sample workout: July 7th morning run (8:08 AM - 9:35 AM)
    test_workout = {
        'startTime': '2025-07-07T08:08:43.000Z',
        'endTime': '2025-07-07T09:35:26.000Z',
        'location': '41.8781,-87.6298'  # Chicago
    }
    
    interpolator = WeatherInterpolator()
    
    print("🌤️  Testing Weather API Integration")
    print("=" * 50)
    
    # Check API key status
    if interpolator.visual_crossing_key:
        print("✅ Visual Crossing API Key: Set")
    else:
        print("❌ Visual Crossing API Key: Not set")
        print("   Get free key at: https://www.visualcrossing.com/weather-api")
    
    if interpolator.openweather_key:
        print("✅ OpenWeatherMap API Key: Set")
    else:
        print("❌ OpenWeatherMap API Key: Not set")
    
    print(f"\n📍 Test Location: Chicago, IL ({test_workout['location']})")
    print(f"🏃 Test Workout: {test_workout['startTime']} → {test_workout['endTime']}")
    print(f"⏱️  Duration: ~87 minutes")
    
    # Test interpolation with 8 splits (typical for 8+ mile run)
    num_splits = 8
    print(f"\n🔢 Requesting {num_splits} split temperatures...")
    
    try:
        temps = interpolator.interpolate_workout_temperatures(
            test_workout['startTime'],
            test_workout['endTime'], 
            num_splits,
            test_workout['location']
        )
        
        print(f"\n🌡️  Temperature Progression:")
        for i, temp in enumerate(temps):
            mile = i + 1
            print(f"   Mile {mile}: {temp}°F")
        
        temp_change = temps[-1] - temps[0]
        print(f"\n📊 Analysis:")
        print(f"   Start Temp: {temps[0]}°F")
        print(f"   End Temp: {temps[-1]}°F") 
        print(f"   Change: {temp_change:+.1f}°F over 87 minutes")
        
        if interpolator.visual_crossing_key:
            print("   ✅ Data Source: Real Historical Weather API")
        else:
            print("   ⚠️  Data Source: Intelligent Time-based Estimates")
    
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_weather_apis() 