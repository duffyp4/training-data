#!/usr/bin/env python3
"""
Test script for weather API integration
"""

import os
from weather_interpolation import WeatherInterpolator

def test_weather_apis():
    """Test weather API integration with sample workout data"""
    
    # Sample workout: July 7th morning run (8:08 AM - 9:35 AM, 8.01 miles)
    test_workout = {
        'startTime': '2025-07-07T08:08:43.000Z',
        'endTime': '2025-07-07T09:35:26.000Z',
        'location': '41.8781,-87.6298'  # Chicago
    }
    
    # Sample splits data (realistic for 8-mile run)
    sample_splits = [
        {'mile': 1, 'mile_time_s': 649},   # 10:49/mile
        {'mile': 2, 'mile_time_s': 651},   # 10:51/mile  
        {'mile': 3, 'mile_time_s': 645},   # 10:45/mile
        {'mile': 4, 'mile_time_s': 648},   # 10:48/mile
        {'mile': 5, 'mile_time_s': 652},   # 10:52/mile
        {'mile': 6, 'mile_time_s': 650},   # 10:50/mile
        {'mile': 7, 'mile_time_s': 647},   # 10:47/mile
        {'mile': 8, 'mile_time_s': 649},   # 10:49/mile
    ]
    
    interpolator = WeatherInterpolator()
    
    print("🌤️  Testing Enhanced Weather API Integration")
    print("=" * 60)
    
    # Check API key status
    if interpolator.visual_crossing_key:
        print("✅ Visual Crossing API Key: Set")
        data_source = "Real Historical Weather API"
    else:
        print("❌ Visual Crossing API Key: Not set")
        print("   Get free key at: https://www.visualcrossing.com/weather-api")
        data_source = "Intelligent Time-based Estimates"
    
    if interpolator.openweather_key:
        print("✅ OpenWeatherMap API Key: Set")
    else:
        print("❌ OpenWeatherMap API Key: Not set")
    
    print(f"\n📍 Test Location: Chicago, IL ({test_workout['location']})")
    print(f"🏃 Test Workout: July 7th, 2025 @ 8:08 AM")
    print(f"⏱️  Duration: 87 minutes (8.01 miles)")
    print(f"🎯 Average Pace: 10:49/mile")
    
    # Test Method 1: Exact temperatures with real split timing
    print(f"\n🎯 Method 1: Exact Temperatures at Each Mile Completion")
    print("   Using real split timing data for precise temperature lookup")
    
    try:
        exact_temps = interpolator.interpolate_workout_temperatures(
            test_workout['startTime'],
            test_workout['endTime'], 
            sample_splits,
            test_workout['location']
        )
        
        print(f"\n🌡️  Exact Temperature at Each Mile Completion:")
        
        current_time = "8:08 AM"
        for i, (temp, split) in enumerate(zip(exact_temps, sample_splits)):
            mile = i + 1
            minutes = split['mile_time_s'] // 60
            seconds = split['mile_time_s'] % 60
            pace = f"{minutes}:{seconds:02d}"
            
            # Calculate completion time
            if i == 0:
                completion_minutes = split['mile_time_s'] // 60
                completion_time = f"8:{8 + completion_minutes:02d} AM"
            else:
                # This is simplified - in reality we'd accumulate the times
                completion_time = f"~8:{18 + i*11:02d} AM"
            
            print(f"   Mile {mile} ({completion_time}): {temp}°F  [Pace: {pace}/mi]")
        
        temp_change = exact_temps[-1] - exact_temps[0]
        print(f"\n📊 Analysis:")
        print(f"   Start Temp: {exact_temps[0]}°F")
        print(f"   End Temp: {exact_temps[-1]}°F") 
        print(f"   Change: {temp_change:+.1f}°F over 87 minutes")
        print(f"   ✅ Data Source: {data_source}")
        
    except Exception as e:
        print(f"❌ Error with exact timing: {e}")
    
    # Test Method 2: Estimated mile times (when split data unavailable)
    print(f"\n🔄 Method 2: Estimated Mile Completion Times")
    print("   For comparison when split timing data is not available")
    
    try:
        estimated_temps = interpolator.interpolate_workout_temperatures(
            test_workout['startTime'],
            test_workout['endTime'], 
            None,  # No splits data
            test_workout['location']
        )
        
        print(f"\n🌡️  Estimated Temperature Progression:")
        for i, temp in enumerate(estimated_temps):
            mile = i + 1
            estimated_time = f"~8:{18 + i*11:02d} AM"
            print(f"   Mile {mile} ({estimated_time}): {temp}°F")
        
        print(f"\n📊 Comparison:")
        if len(exact_temps) == len(estimated_temps):
            avg_diff = sum(abs(e - est) for e, est in zip(exact_temps, estimated_temps)) / len(exact_temps)
            print(f"   Average difference: {avg_diff:.1f}°F between exact vs estimated")
        
    except Exception as e:
        print(f"❌ Error with estimated timing: {e}")
    
    print(f"\n🚀 Key Benefits of Exact Timing:")
    print(f"   • Real temperature at each mile completion time")
    print(f"   • No linear interpolation assumptions")
    print(f"   • Accounts for actual workout pace variations")
    print(f"   • More accurate for performance analysis")

if __name__ == "__main__":
    test_weather_apis() 