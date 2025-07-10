#!/usr/bin/env python3
"""
Test script to investigate Garmin Connect API endpoints locally
and identify what enhanced data is available without FIT downloads.
"""

import os
import json
import garth
import logging
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def authenticate_garmin():
    """Authenticate with Garmin Connect"""
    try:
        email = os.getenv('GARMIN_EMAIL')
        password = os.getenv('GARMIN_PASSWORD')
        
        if not email or not password:
            logger.error("GARMIN_EMAIL and GARMIN_PASSWORD must be set in .env file")
            return False
            
        logger.info("Authenticating with Garmin Connect...")
        garth.client.configure(domain="garmin.com")
        garth.login(email, password)
        logger.info("✅ Authentication successful!")
        return True
        
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        return False

def test_activity_details(activity_id: str):
    """Test detailed activity endpoint to see what enhanced data is available"""
    logger.info(f"\n🔍 Testing Activity Details for ID: {activity_id}")
    
    try:
        # Test basic activity summary
        logger.info("--- Basic Activity Summary ---")
        activities = garth.connectapi(f"/activitylist-service/activities/search/activities", params={
            "activityType": "running",
            "limit": 1,
            "start": 0
        })
        if activities:
            logger.info("Basic activity data structure:")
            logger.info(json.dumps(activities[0] if isinstance(activities, list) else activities, indent=2, default=str)[:1500] + "...")
        
        # Test detailed activity data
        logger.info("\n--- Detailed Activity Data ---")
        detailed = garth.connectapi(f"/activity-service/activity/{activity_id}")
        if detailed:
            logger.info("🎯 DETAILED ACTIVITY RESPONSE:")
            logger.info(json.dumps(detailed, indent=2, default=str)[:3000] + "...")
            
            # Look for specific enhanced features
            enhanced_features = {}
            if 'trainingEffectLabel' in str(detailed):
                enhanced_features['training_effects'] = "Found training effect data!"
            if 'location' in str(detailed).lower() or 'gps' in str(detailed).lower():
                enhanced_features['location'] = "Found location data!"
            if 'heartRate' in str(detailed) or 'hrZone' in str(detailed):
                enhanced_features['hr_zones'] = "Found heart rate zone data!"
            if 'cadence' in str(detailed).lower() or 'stride' in str(detailed).lower():
                enhanced_features['running_dynamics'] = "Found running dynamics!"
                
            if enhanced_features:
                logger.info("\n🎉 ENHANCED FEATURES FOUND:")
                for feature, status in enhanced_features.items():
                    logger.info(f"  • {feature}: {status}")
            else:
                logger.info("\n❌ No obvious enhanced features found in detailed activity")
                
    except Exception as e:
        logger.error(f"Error testing activity details: {e}")

def test_splits_data(activity_id: str):
    """Test activity splits endpoint for enhanced split data"""
    logger.info(f"\n🔍 Testing Activity Splits for ID: {activity_id}")
    
    try:
        splits = garth.connectapi(f"/activity-service/activity/{activity_id}/splits")
        if splits:
            logger.info("🎯 SPLITS RESPONSE:")
            logger.info(json.dumps(splits, indent=2, default=str)[:2000] + "...")
            
            # Look for enhanced split features
            enhanced_split_features = {}
            if 'cadence' in str(splits).lower():
                enhanced_split_features['cadence'] = "Found cadence data!"
            if 'stride' in str(splits).lower():
                enhanced_split_features['stride_length'] = "Found stride length!"
            if 'groundContact' in str(splits) or 'verticalOscillation' in str(splits):
                enhanced_split_features['running_dynamics'] = "Found running dynamics!"
            if 'stepType' in str(splits) or 'lapType' in str(splits):
                enhanced_split_features['step_types'] = "Found step/lap types!"
                
            if enhanced_split_features:
                logger.info("\n🎉 ENHANCED SPLIT FEATURES FOUND:")
                for feature, status in enhanced_split_features.items():
                    logger.info(f"  • {feature}: {status}")
            else:
                logger.info("\n❌ No obvious enhanced features found in splits")
        else:
            logger.warning("No splits data returned")
            
    except Exception as e:
        logger.error(f"Error testing splits data: {e}")

def test_wellness_endpoints(date_str: str = "2025-06-13"):
    """Test wellness endpoints to see what data is available"""
    logger.info(f"\n🔍 Testing Wellness Endpoints for date: {date_str}")
    
    endpoints_to_test = [
        f"/wellness-service/wellness/dailyHeartRate/{date_str}",
        f"/wellness-service/wellness/dailySleepData/{garth.client.username}?date={date_str}",
        f"/wellness-service/wellness/bodyBatteryEvents",
        f"/usersummary-service/usersummary/daily/{garth.client.username}?calendarDate={date_str}",
    ]
    
    for endpoint in endpoints_to_test:
        try:
            logger.info(f"\n--- Testing: {endpoint} ---")
            response = garth.connectapi(endpoint)
            if response:
                logger.info("✅ Response received:")
                logger.info(json.dumps(response, indent=2, default=str)[:1000] + "...")
                
                # Look for specific wellness features
                if 'hrZone' in str(response) or 'zone' in str(response).lower():
                    logger.info("🎯 Found HR zone data!")
                if 'sleep' in str(response).lower() and not str(response) == '{}':
                    logger.info("🎯 Found sleep data!")
                if 'bodyBattery' in str(response) or 'battery' in str(response).lower():
                    logger.info("🎯 Found body battery data!")
            else:
                logger.warning("❌ No response data")
                
        except Exception as e:
            logger.warning(f"Error testing {endpoint}: {e}")

def main():
    """Main test function"""
    logger.info("=== GARMIN API ENDPOINT INVESTIGATION ===\n")
    
    # Authenticate
    if not authenticate_garmin():
        return
    
    # Get the most recent activity ID from last_id.json
    try:
        with open('../data/last_id.json', 'r') as f:
            last_data = json.load(f)
            test_activity_id = last_data.get('last_id', '12015116894')  # June 13th activity
    except:
        test_activity_id = '12015116894'  # Fallback to known activity
    
    logger.info(f"Using test activity ID: {test_activity_id}")
    
    # Test the endpoints
    test_activity_details(test_activity_id)
    test_splits_data(test_activity_id)
    test_wellness_endpoints("2025-06-13")
    
    logger.info("\n" + "="*60)
    logger.info("🎯 INVESTIGATION COMPLETE")
    logger.info("Check the logs above for enhanced data availability!")
    logger.info("="*60)

if __name__ == "__main__":
    main() 