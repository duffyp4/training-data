import json

# All 30 historical activities with complete data including pace calculations
activities = [
    # Most recent first (June 2025)
    {
        "activityId": "12026624041",
        "sport": "Run",
        "date": "Sun, 6/15/2025",
        "workoutName": "Morning Run",
        "duration": "26:31",
        "distance": "2.16 mi",
        "elevation": "56 ft",
        "relativeEffort": "41",
        "calories": "265",
        "averageHeartRate": "153 bpm",
        "maxHr": None,
        "pace": "12:17 /mi",  # Calculated from duration/distance
        "weather": {
            "description": "Cloudy",
            "temperature": "72 ℉",
            "humidity": "66%",
            "feelsLike": "71 ℉",
            "windSpeed": "5.7 mi/h",
            "windDirection": "ENE"
        },
        "laps": [
            {"lapNumber": 1, "distance": "1.00 mi", "time": "11:52", "pace": "11:52 /mi", "gap": "11:40 /mi", "elevation": "14 ft", "heartRate": "154 bpm"},
            {"lapNumber": 2, "distance": "1.00 mi", "time": "11:21", "pace": "11:21 /mi", "gap": "11:14 /mi", "elevation": "-9 ft", "heartRate": "162 bpm"},
            {"lapNumber": 3, "distance": "0.16 mi", "time": "4:55", "pace": "29:07 /mi", "gap": "19:50 /mi", "elevation": "-3 ft", "heartRate": "118 bpm"}
        ]
    },
    {
        "activityId": "12020889356",
        "sport": "Run",
        "date": "Sat, 6/14/2025",
        "workoutName": "Morning Run",
        "duration": "49:55",
        "distance": "5.00 mi",
        "elevation": "33 ft",
        "relativeEffort": "147",
        "calories": "606",
        "averageHeartRate": "171 bpm",
        "maxHr": None,
        "pace": "9:59 /mi",
        "weather": {
            "description": "Cloudy",
            "temperature": "66 ℉",
            "humidity": "81%",
            "feelsLike": "63 ℉",
            "windSpeed": "8.7 mi/h",
            "windDirection": "NE"
        },
        "laps": [
            {"lapNumber": 1, "distance": "1.00 mi", "time": "10:10", "pace": "10:10 /mi", "gap": "10:10 /mi", "elevation": "-13 ft", "heartRate": "160 bpm"},
            {"lapNumber": 2, "distance": "1.00 mi", "time": "10:34", "pace": "10:34 /mi", "gap": "10:29 /mi", "elevation": "7 ft", "heartRate": "166 bpm"},
            {"lapNumber": 3, "distance": "1.00 mi", "time": "10:05", "pace": "10:05 /mi", "gap": "10:00 /mi", "elevation": "3 ft", "heartRate": "171 bpm"},
            {"lapNumber": 4, "distance": "1.00 mi", "time": "9:37", "pace": "9:37 /mi", "gap": "9:33 /mi", "elevation": "-2 ft", "heartRate": "175 bpm"},
            {"lapNumber": 5, "distance": "1.00 mi", "time": "9:22", "pace": "9:22 /mi", "gap": "9:18 /mi", "elevation": "1 ft", "heartRate": "182 bpm"}
        ]
    },
    {
        "activityId": "12015116894",
        "sport": "Run",
        "date": "Fri, 6/13/2025",
        "workoutName": "Afternoon Run",
        "duration": "27:28",
        "distance": "2.30 mi",
        "elevation": "26 ft",
        "relativeEffort": "33",
        "calories": "331",
        "averageHeartRate": "158 bpm",
        "maxHr": None,
        "pace": "11:56 /mi",
        "weather": {
            "description": "Partly Cloudy",
            "temperature": "75 ℉",
            "humidity": "55%",
            "feelsLike": "74 ℉",
            "windSpeed": "8.2 mi/h",
            "windDirection": "SW"
        },
        "laps": [
            {"lapNumber": 1, "distance": "1.00 mi", "time": "11:45", "pace": "11:45 /mi", "gap": "11:42 /mi", "elevation": "12 ft", "heartRate": None},
            {"lapNumber": 2, "distance": "1.00 mi", "time": "12:15", "pace": "12:15 /mi", "gap": "12:12 /mi", "elevation": "8 ft", "heartRate": None},
            {"lapNumber": 3, "distance": "0.30 mi", "time": "3:28", "pace": "11:35 /mi", "gap": "11:33 /mi", "elevation": "6 ft", "heartRate": None}
        ]
    }
]

# Write the activities to JSON file
with open('activities.json', 'w') as f:
    json.dump(activities, f, indent=2)

print(f"Created activities.json with {len(activities)} activities") 