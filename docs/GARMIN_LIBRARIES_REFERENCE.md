# Garmin Libraries Technical Reference

This document captures hard-won knowledge about working with Garmin Connect APIs through the `garth` and `python-garminconnect` libraries, based on extensive trial-and-error debugging in July 2025.

## 📚 Library Overview

### **garth** - Modern Garmin Connect API Client
- **Current Version**: 0.5.17+ (critical for wellness data)
- **Strengths**: Modern helper classes, active development, handles new API patterns
- **Best For**: Wellness data, activity details, modern API endpoints
- **Authentication**: OAuth-based with session persistence

### **python-garminconnect** - Legacy Garmin Connect Client  
- **Latest Version**: 0.1.56+ (updated for new endpoints)
- **Strengths**: Mature, stable, some unique endpoints
- **Best For**: Resting heart rate, some wellness endpoints
- **Note**: Not currently used in our implementation but documented for reference

## 🚨 Critical API Changes (2024-2025)

### **Endpoint Reshuffles** 
The Garmin Connect API underwent **two major reshuffles**:
- **October 2024**: Initial wellness endpoint changes
- **March 2025**: Second round of wellness API restructuring

### **Impact on Our System**
- **Old manual endpoints**: Started returning 403/404 errors
- **Library updates required**: garth 0.5.17+ includes new helper classes
- **URL patterns changed**: Wellness endpoints moved to new paths
- **Authentication requirements**: Some endpoints now require additional headers/params

## ✅ Working Wellness Data Methods (Verified July 2025)

### **Daily Steps** 
```python
import garth
garth.login(email, password)

# ✅ WORKING METHOD
steps_data = garth.DailySteps.list("2025-07-07")
if steps_data and len(steps_data) > 0:
    total_steps = steps_data[0].total_steps  # → 29,901
```

**Key Insights:**
- Uses `.list()` method, not `.get()`
- Returns array, take first element `[0]`
- Attribute is `total_steps` not `steps`

### **Body Battery**
```python
# ✅ WORKING METHOD  
bb_data = garth.DailyBodyBatteryStress.get("2025-07-07")
max_battery = bb_data.max_body_battery      # → 72
min_battery = bb_data.min_body_battery      # → 23
current_battery = bb_data.current_body_battery
```

**Key Insights:**
- Uses `.get()` method (different from DailySteps)
- Multiple attributes available for analysis
- Reliable and consistently works

### **Resting Heart Rate**
```python
# ✅ WORKING METHOD
rhr_data = garth.connectapi("/wellness-service/wellness/dailyHeartRate", 
                           params={"date": "2025-07-07"})
resting_hr = rhr_data.get('restingHeartRate')  # → 50
```

**Key Insights:**
- Requires `params={"date": date}` format, not date in URL path
- Different pattern from other wellness endpoints
- Returns dictionary, extract `restingHeartRate` key

### **HRV (Heart Rate Variability)**
```python
# ✅ WORKING METHOD (unchanged)
hrv_data = garth.connectapi(f"/hrv-service/hrv/{date}")
hrv_value = hrv_data.get('lastNightAvg')  # → 37
```

**Key Insights:**
- This endpoint didn't change in the reshuffles
- Still works with date in URL path
- Reliable method, no issues

## ❌ Failed Endpoints (What Doesn't Work)

### **Old Manual Wellness Endpoints**
```python
# ❌ THESE FAIL (403/404 errors)
garth.connectapi(f"/wellness-service/wellness/dailySummaryChart/{date}")
garth.connectapi(f"/wellness-service/wellness/bodyBattery/reports/daily/{date}")  
garth.connectapi(f"/wellness-service/wellness/dailyHeartRate/{date}")  # Old format
```

**Error Patterns:**
- **403 Forbidden**: Endpoint exists but auth/headers insufficient
- **404 Not Found**: Endpoint path no longer exists
- **Root Cause**: Oct 2024 & Mar 2025 API reshuffles made these obsolete

## 🔧 Authentication Patterns

### **Basic Authentication**
```python
import garth
from dotenv import load_dotenv
import os

# Load credentials
load_dotenv()
email = os.getenv('GARMIN_EMAIL')
password = os.getenv('GARMIN_PASSWORD')

# Authenticate
garth.login(email, password)

# Session persists for subsequent API calls
```

### **Session Persistence**
```python
# Save session (optional)
garth.save("~/.garth")

# Resume session (optional)
garth.resume("~/.garth")
```

### **2FA Support**
```python
# If 2FA enabled on account
totp_secret = os.getenv('GARMIN_2FA_SECRET')  
garth.login(email, password, totp_secret)
```

## 📊 Working Activity Data Methods

### **Recent Activities**
```python
# Get recent activities (works reliably)
activities = garth.connectapi("/activitylist-service/activities/search/activities", 
                              params={"limit": 50})
```

### **Detailed Activity Data**
```python
# Get enhanced activity details
activity_id = "19680128748"
detailed_activity = garth.connectapi(f"/activity-service/activity/{activity_id}")

# Extract enhanced features
training_effects = detailed_activity.get('summaryDTO', {})
location_data = detailed_activity.get('locationName')  # → "Chicago, IL"
```

### **Splits Data**  
```python
# Get per-split data with running dynamics
splits_data = garth.connectapi(f"/activity-service/activity/{activity_id}/splits")
for split in splits_data.get('lapDTOs', []):
    cadence = split.get('averageRunCadence')
    stride_length = split.get('averageStrideLength') 
    # + 40+ other metrics per split
```

## 🐛 Troubleshooting Guide

### **Common Error Codes**
| Code | Meaning | Solution |
|------|---------|----------|
| **403** | Auth rejected | Check credentials, try different endpoint format |
| **404** | Endpoint not found | Use new helper classes instead of manual URLs |
| **429** | Rate limited | Add delays between requests |
| **500** | Server error | Retry with exponential backoff |

### **Wellness Data Debugging Steps**
1. **Check library version**: `pip show garth` → Must be 0.5.17+
2. **Test authentication**: Verify login works with simple activity call
3. **Use helper classes**: Avoid manual API endpoints for wellness data
4. **Check date format**: Use "YYYY-MM-DD" string format
5. **Verify data availability**: Some metrics may not be available for all dates

### **API Response Patterns**
```python
# Always check for data existence
if response and isinstance(response, dict):
    # Process data
    value = response.get('key')
else:
    # Handle missing/invalid response
    logger.warning(f"No data returned for {endpoint}")
```

## 🎯 Best Practices

### **Error Handling**
```python
def get_wellness_data_safely(date):
    try:
        steps_data = garth.DailySteps.list(date)
        if steps_data and len(steps_data) > 0:
            return steps_data[0].total_steps
    except Exception as e:
        logger.warning(f"Failed to get steps for {date}: {e}")
        return None
```

### **Rate Limiting**
```python
import time

# Add delays between API calls
time.sleep(0.5)  # 500ms between requests
```

### **Data Validation**
```python
# Always validate data types and ranges
if isinstance(steps, int) and 0 <= steps <= 100000:
    # Reasonable step count
    return steps
else:
    logger.warning(f"Invalid step count: {steps}")
    return None
```

## 🔄 Migration Guide (Old → New)

### **Steps Data**
```python
# ❌ OLD (broken)
steps_data = garth.connectapi(f"/wellness-service/wellness/dailySummaryChart/{date}")
steps = steps_data['summaryList'][0]['value']

# ✅ NEW (working)  
steps_data = garth.DailySteps.list(date)
steps = steps_data[0].total_steps if steps_data else None
```

### **Body Battery** 
```python
# ❌ OLD (broken)
bb_data = garth.connectapi(f"/wellness-service/wellness/bodyBattery/reports/daily/{date}")

# ✅ NEW (working)
bb_data = garth.DailyBodyBatteryStress.get(date)
max_bb = bb_data.max_body_battery
```

### **Resting Heart Rate**
```python
# ❌ OLD (broken)
rhr_data = garth.connectapi(f"/wellness-service/wellness/dailyHeartRate/{date}")

# ✅ NEW (working)
rhr_data = garth.connectapi("/wellness-service/wellness/dailyHeartRate", 
                           params={"date": date})
rhr = rhr_data.get('restingHeartRate')
```

## 📈 Performance Considerations

### **Batch Processing**
- Group API calls where possible
- Use date ranges for bulk data retrieval
- Cache responses for repeated queries

### **Monitoring**
```python
import logging

# Enable detailed logging for troubleshooting
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Log API calls for debugging
logger.debug(f"Calling API: {endpoint}")
```

## 🔮 Future Considerations

### **Library Updates**
- Monitor garth releases for new helper classes
- Test wellness endpoints after any library updates
- Keep backup of working endpoint patterns

### **API Evolution**
- Garmin may introduce additional endpoint changes
- Helper classes provide abstraction from raw endpoints
- Document any new working patterns discovered

## 📋 Testing Checklist

When testing new Garmin integrations:

- [ ] Verify library versions (garth 0.5.17+)
- [ ] Test authentication with simple API call
- [ ] Validate wellness data helper methods  
- [ ] Check activity data retrieval
- [ ] Test with recent dates (within 7 days)
- [ ] Verify data types and reasonable ranges
- [ ] Test error handling for missing data
- [ ] Add appropriate logging for debugging

---

**Document Created**: July 9, 2025  
**Library Versions Tested**: garth 0.5.17  
**API Status**: ✅ All wellness endpoints working via helper classes  
**Last Verified**: July 2025 with complete success on multiple dates

**Key Insight**: The API reshuffles broke manual endpoint calls, but garth 0.5.17+ helper classes abstract these changes and provide reliable access to all wellness data. 