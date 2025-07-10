# Garmin Training Data Repository

This repository automatically collects and processes comprehensive Garmin Connect training data into structured daily files with complete wellness metrics, enhanced workout data, and weather integration.

## 🚀 Live Data

**View the latest training data:** [https://duffyp4.github.io/training-data/](https://duffyp4.github.io/training-data/)

The system runs automatically every night at **6 AM UTC (midnight CDT)** via GitHub Actions.

## ✨ Features

### 📊 **Complete Wellness Data**
- **Daily Steps**: Real device step counts (29,901 steps)
- **Body Battery**: Charge/drain throughout the day (+15 charged, -45 drained)
- **Resting Heart Rate**: Daily resting HR measurements (49 bpm)
- **HRV (Heart Rate Variability)**: Sleep recovery metrics (38 ms)

### 🏃 **Enhanced Workout Metrics**
- **Training Effects**: Aerobic (4.2) • Anaerobic (0.3) • Training labels (TEMPO)
- **Running Dynamics**: Cadence, stride length, ground contact time, vertical oscillation
- **Power Data**: Average, max, normalized power + 5-zone time distribution
- **GPS Location**: Converts coordinates to city names ("Chicago, IL")
- **Weather Integration**: Visual Crossing API for start/end workout weather
- **Per-Split Data**: Mile-by-mile dynamics, power zones, and detailed metrics

### 😴 **Sleep & Recovery**
- **Sleep Stages**: Deep, Light, REM, and Awake time breakdown
- **Sleep Score**: Garmin's overall sleep quality rating (91/100)
- **HRV**: Nighttime heart rate variability for recovery tracking

## 📁 Data Structure

```
data/
├── last_id.json              # Tracks last processed activity
├── index.md                  # Human-readable index of all files
└── YYYY/
    └── MM/
        └── DD.md            # Daily summary with YAML + Markdown
```

## 🔧 Core Scripts

### **Data Collection Pipeline**

1. **`garmin_scraper.py`** - Authenticates with Garmin Connect and retrieves:
   - Activity data with enhanced metrics
   - Wellness data (steps, body battery, resting HR)
   - Sleep data with stages and HRV
   - Splits data with running dynamics

2. **`garmin_to_daily_files.py`** - Processes raw data into structured files:
   - Groups activities by date
   - Adds location lookup (coordinates → city)
   - Integrates Visual Crossing weather data
   - Formats human-readable summaries
   - Generates YAML front matter + Markdown

3. **`generate_index.py`** - Creates the main index page with:
   - Chronological list of all training days
   - Quick links to each daily summary
   - Total file count and date range

## ⚙️ Configuration

### **Environment Variables**
Create a `.env` file with your credentials:

```env
# Required: Garmin Connect credentials
GARMIN_EMAIL=your_email@example.com
GARMIN_PASSWORD=your_password

# Required: Weather data integration  
VISUAL_CROSSING_API_KEY=your_api_key

# Optional: 2FA (if enabled on your account)
GARMIN_2FA_SECRET=your_2fa_secret
```

### **API Keys**
- **Visual Crossing Weather API**: Get free API key at [visualcrossing.com](https://www.visualcrossing.com/weather-api) (1000 calls/day free)

## 🤖 Automated Workflow

### **GitHub Actions Schedule**
- **Runs:** Daily at 6 AM UTC (midnight CDT)
- **Triggers:** Automatic schedule + manual workflow dispatch
- **Process:**
  1. Scrapes new Garmin data since last run
  2. Processes into daily files with all enhanced features
  3. Generates updated index
  4. Commits and pushes to GitHub

### **Manual Triggering**
1. Go to **Actions** tab in GitHub
2. Select **"Nightly Garmin Sync"**
3. Click **"Run workflow"**
4. Optionally specify an activity ID for refresh

## 📊 Data Format

### **YAML Front Matter**
```yaml
date: '2025-07-09'
schema: 2
sleep_metrics:
  sleep_minutes: 440
  deep_minutes: 88
  light_minutes: 233
  rem_minutes: 119
  sleep_score: 91
  hrv_night_avg: 38
daily_metrics:
  body_battery:
    charge: 15
    drain: 45
  steps: 29901
  resting_hr: 49
workout_metrics:
- id: 19680128748
  type: Run
  location: Chicago, IL
  weather:
    temperature:
      start: 68
      end: 71
    conditions: Partially cloudy
  training_effects:
    aerobic: 4.2
    anaerobic: 0.3
    label: TEMPO
  running_dynamics:
    cadence_spm: 164.64
    stride_length_cm: 90.35
    ground_contact_time_ms: 273.5
    vertical_oscillation_mm: 8.04
  power_zones:
    zone_1: '9:58'
    zone_2: '57:34'
    zone_3: '11:16'
    zone_4: '2:53'
    zone_5: '0:28'
```

### **Human-Readable Output**
```markdown
# 2025-07-09 · Daily Summary
**Totals:** 13.1 mi • 1h 22m 9s • 177 ft ↑ • 29,901 steps  
**Sleep:** 7h 20m sleep

## Sleep Metrics
**Total Sleep:** 7h 20m
**Sleep Stages:** Deep: 88m • Light: 233m • REM: 119m
**Sleep Score:** 91
**HRV:** 38 ms

## Daily Metrics
**Steps:** 29,901
**Body Battery:** Charged: +15 • Drained: -45
**Resting Heart Rate:** 49 bpm

## Workout Details
### Run
**Distance & Time:** 13.11 mi • 1h 22m 9s • 177 ft ↑
**Location:** Chicago, IL
**Weather:** 68°F → 71°F • 75% → 68% humidity • Partially cloudy
**Training Effects:** Aerobic: 4.2 • Anaerobic: 0.3 • (TEMPO)
**Running Dynamics:** Cadence: 164.64 spm • Stride: 90.35 cm
**Power Zones:** Z1: 9:58 • Z2: 57:34 • Z3: 11:16 • Z4: 2:53 • Z5: 0:28
```

## 🛠️ Local Development

### **Setup**
```bash
# Install dependencies
pip install -r requirements.txt

# Run scraper manually  
python3 scripts/garmin_scraper.py

# Process data into daily files
python3 scripts/garmin_to_daily_files.py

# Generate index
python3 scripts/generate_index.py
```

### **Dependencies**
- **garth 0.5.17+**: Garmin Connect API with modern wellness helpers
- **python-dotenv**: Environment variable management
- **requests**: HTTP requests for weather API
- **python-dateutil**: Date parsing and timezone handling

## 🔍 Technical Details

### **Data Sources**
- **Garmin Connect API**: Activities, wellness, sleep data
- **Visual Crossing Weather API**: Historical weather for workout locations
- **Enhanced APIs**: Uses latest garth 0.5.17+ helper methods for reliable wellness data

### **Key Improvements (2025)**
- ✅ **Wellness Data Fixed**: Updated to use `garth.DailySteps.list()` and `garth.DailyBodyBatteryStress.get()`
- ✅ **Weather Integration**: Real-time weather data for all workout locations
- ✅ **Training Effects**: Aerobic/anaerobic training effect scores and labels
- ✅ **Running Dynamics**: Complete biomechanical data per activity and split
- ✅ **Power Zones**: Time-in-zone analysis across 5 power zones

### **Error Handling**
- Graceful API failure handling with detailed logging
- Automatic retry logic for transient failures
- Maintains data consistency across runs
- Preserves partial data when individual metrics fail

## 📈 Data Quality

The system ensures high data quality through:
- **Source Verification**: All data pulled directly from Garmin APIs [[memory:2726865]]
- **Real Device Data**: Steps, HRV, body battery from actual device sensors
- **Weather Accuracy**: Historical weather data matched to workout time/location
- **Comprehensive Logging**: Detailed logs for troubleshooting and verification

---

**Last Updated:** July 2025  
**Status:** ✅ Fully operational with complete wellness data integration 