#!/usr/bin/env python3
"""
Test script to get a recent activity and test enhanced endpoints
"""

import os
import json
import garth
import logging
from dotenv import load_dotenv

load_dotenv()
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

def get_recent_activity():
    """Get the most recent running activity"""
    try:
        logger.info("Getting recent activities...")
        activities = garth.connectapi(f"/activitylist-service/activities/search/activities", params={
            "activityType": "running",
            "limit": 3,
            "start": 0
        })
        
        if activities and len(activities) > 0:
            recent = activities[0]
            activity_id = recent.get('activityId')
            activity_name = recent.get('activityName', 'Unknown')
            start_time = recent.get('startTimeLocal', 'Unknown')
            
            logger.info(f"✅ Found recent activity:")
            logger.info(f"  • ID: {activity_id}")
            logger.info(f"  • Name: {activity_name}")
            logger.info(f"  • Date: {start_time}")
            
            # Show what enhanced data is already in basic response
            logger.info(f"\n🎯 ENHANCED DATA ALREADY AVAILABLE:")
            if 'startLatitude' in recent and 'startLongitude' in recent:
                lat, lon = recent['startLatitude'], recent['startLongitude']
                logger.info(f"  • GPS Location: {lat}, {lon}")
            
            if 'averageRunningCadenceInStepsPerMinute' in recent:
                cadence = recent['averageRunningCadenceInStepsPerMinute']
                logger.info(f"  • Running Cadence: {cadence} steps/min")
                
            if 'calories' in recent:
                calories = recent['calories']
                logger.info(f"  • Calories: {calories}")
                
            # Look for other potential enhancements
            interesting_fields = []
            for key in recent.keys():
                if any(term in key.lower() for term in ['effect', 'training', 'power', 'stride', 'ground', 'vertical']):
                    interesting_fields.append(f"{key}: {recent[key]}")
            
            if interesting_fields:
                logger.info(f"\n🔍 Other interesting fields found:")
                for field in interesting_fields:
                    logger.info(f"  • {field}")
            
            return activity_id
        else:
            logger.error("No activities found")
            return None
            
    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        return None

def test_enhanced_endpoints(activity_id):
    """Test enhanced endpoints with a recent activity ID"""
    logger.info(f"\n🔍 Testing Enhanced Endpoints for recent activity: {activity_id}")
    
    # Test detailed activity
    try:
        logger.info("--- Testing Detailed Activity ---")
        detailed = garth.connectapi(f"/activity-service/activity/{activity_id}")
        if detailed:
            logger.info("✅ Detailed activity data received!")
            
            # Look for training effects
            training_effect_fields = []
            for key, value in detailed.items():
                if 'effect' in key.lower() or 'training' in key.lower():
                    training_effect_fields.append(f"{key}: {value}")
            
            if training_effect_fields:
                logger.info("🎯 TRAINING EFFECT DATA FOUND:")
                for field in training_effect_fields:
                    logger.info(f"  • {field}")
            
            # Look for other enhanced metrics
            enhanced_fields = []
            search_terms = ['zone', 'hr', 'heartrate', 'power', 'pace', 'speed', 'weather', 'temperature']
            for key, value in detailed.items():
                if any(term in key.lower() for term in search_terms) and key not in ['averageHR', 'maxHR']:
                    enhanced_fields.append(f"{key}: {value}")
            
            if enhanced_fields:
                logger.info("🔍 Other enhanced fields:")
                for field in enhanced_fields[:10]:  # Limit output
                    logger.info(f"  • {field}")
                    
            logger.info(f"📊 Total fields in detailed response: {len(detailed)}")
            
        else:
            logger.warning("No detailed activity data")
            
    except Exception as e:
        logger.error(f"Error testing detailed activity: {e}")
    
    # Test splits
    try:
        logger.info("\n--- Testing Activity Splits ---")
        splits = garth.connectapi(f"/activity-service/activity/{activity_id}/splits")
        if splits:
            logger.info("✅ Splits data received!")
            
            if isinstance(splits, dict) and 'lapDTOs' in splits:
                laps = splits['lapDTOs']
                logger.info(f"📊 Found {len(laps)} laps/splits")
                
                if laps:
                    first_lap = laps[0]
                    logger.info("🔍 First lap fields:")
                    for key, value in first_lap.items():
                        if any(term in key.lower() for term in ['cadence', 'stride', 'contact', 'vertical', 'power', 'step']):
                            logger.info(f"  • {key}: {value}")
                    
                    logger.info(f"📋 Total fields per lap: {len(first_lap)}")
            else:
                logger.info("🔍 Splits structure:")
                logger.info(json.dumps(splits, indent=2, default=str)[:1000] + "...")
                
        else:
            logger.warning("No splits data")
            
    except Exception as e:
        logger.error(f"Error testing splits: {e}")

def main():
    """Main test function"""
    logger.info("=== TESTING RECENT ACTIVITY FOR ENHANCED DATA ===\n")
    
    if not authenticate_garmin():
        return
    
    # Get recent activity ID
    activity_id = get_recent_activity()
    if not activity_id:
        return
    
    # Test enhanced endpoints
    test_enhanced_endpoints(activity_id)
    
    logger.info("\n" + "="*60)
    logger.info("🎯 RECENT ACTIVITY TESTING COMPLETE")
    logger.info("="*60)

if __name__ == "__main__":
    main() 