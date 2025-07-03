#!/usr/bin/env python3
"""
Garmin Renderer
Converts Garmin activities to the same JSON-LD format as existing Strava data
Maintains backward compatibility while adding enhanced data fields
"""

import json
import os
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GarminRenderer:
    def __init__(self):
        self.index_path = Path("index.md")
        self.last_id_path = Path("data/last_id.json")
        self.activities_path = Path("activities.json")

    def get_existing_ids(self) -> set:
        """Extract all activity IDs from existing index.md"""
        try:
            content = self.index_path.read_text()
            ids = set()
            # Find all identifier fields in JSON-LD blocks
            pattern = r'"identifier": "(\d+)"'
            matches = re.findall(pattern, content)
            ids.update(matches)
            logger.info(f"Found {len(ids)} existing activities in {self.index_path}")
            return ids
        except FileNotFoundError:
            logger.info("index.md not found. A new one will be created.")
            return set()

    def get_existing_datetime_signatures(self) -> set:
        """Extract datetime signatures from existing activities for duplicate detection"""
        signatures = set()
        try:
            content = self.index_path.read_text()
            # Find all JSON-LD blocks
            pattern = r'```jsonld\n(.*?)\n```'
            matches = re.findall(pattern, content, re.DOTALL)
            
            for match in matches:
                try:
                    activity = json.loads(match)
                    signature = self.create_datetime_signature_from_jsonld(activity)
                    if signature:
                        signatures.add(signature)
                except json.JSONDecodeError:
                    continue
                    
            logger.info(f"Created {len(signatures)} datetime signatures from existing activities")
            return signatures
        except FileNotFoundError:
            return set()

    def create_datetime_signature_from_jsonld(self, activity: Dict) -> Optional[str]:
        """Create datetime signature from JSON-LD activity data"""
        try:
            start_time = activity.get('startTime', '')
            duration = activity.get('duration', '')
            distance = activity.get('distance', '')
            
            if start_time and duration and distance:
                # Extract date part from ISO timestamp
                date_part = start_time.split('T')[0] if 'T' in start_time else start_time[:10]
                return f"{date_part}_{duration}_{distance}"
        except Exception as e:
            logger.debug(f"Could not create signature: {e}")
        return None

    def create_datetime_signature(self, activity: Dict) -> Optional[str]:
        """Create datetime signature from Garmin activity data"""
        try:
            date = activity.get('date', '')
            duration = activity.get('duration', '')
            distance = activity.get('distance', '')
            
            if date and duration and distance:
                # Extract just the date part if it contains day name
                if ',' in date:
                    date_part = date.split(',')[1].strip()
                    # Convert M/D/YYYY to YYYY-MM-DD format
                    dt = datetime.strptime(date_part, "%m/%d/%Y")
                    date_normalized = dt.strftime("%Y-%m-%d")
                else:
                    date_normalized = date
                
                return f"{date_normalized}_{duration}_{distance}"
        except Exception as e:
            logger.debug(f"Could not create signature from activity: {e}")
        return None

    def update_last_id(self, newest_activity: Dict):
        """Update the last_id.json file with the newest activity"""
        last_data = {
            "last_id": newest_activity["activityId"],
            "last_date": newest_activity.get("date", "")
        }
        
        # Ensure data directory exists
        self.last_id_path.parent.mkdir(exist_ok=True)
        
        with open(self.last_id_path, 'w') as f:
            json.dump(last_data, f, indent=2)
        
        logger.info(f"Updated last_id.json to: ID={newest_activity['activityId']}, Date={newest_activity.get('date', '')}")

    def parse_duration_to_iso_duration(self, duration_str: str, start_time: str) -> str:
        """Convert duration string to ISO end time"""
        if not duration_str or not start_time:
            return ""
        
        try:
            # Parse duration like "35:49" or "1:02:08"
            parts = duration_str.split(':')
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                total_seconds = minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                total_seconds = hours * 3600 + minutes * 60 + seconds
            else:
                return ""
            
            # Add duration to start time
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            end_dt = start_dt.replace(microsecond=0) + timedelta(seconds=total_seconds)
            return end_dt.isoformat() + 'Z'
        except Exception as e:
            logger.warning(f"Could not parse duration '{duration_str}': {e}")
            return ""

    def parse_date_to_iso(self, date_str: str) -> str:
        """Convert date string to ISO format"""
        if not date_str:
            return ""
        
        try:
            # Handle format like "Tue, 7/1/2025"
            if ',' in date_str:
                date_part = date_str.split(',')[1].strip()
                dt = datetime.strptime(date_part, "%m/%d/%Y")
                return dt.isoformat() + '.000Z'
        except Exception as e:
            logger.warning(f"Could not parse date '{date_str}': {e}")
        
        return ""

    def to_markdown(self, activity: Dict) -> str:
        """Convert activity to markdown with JSON-LD"""
        
        # Parse start and end times
        start_time = self.parse_date_to_iso(activity.get("date", ""))
        end_time = self.parse_duration_to_iso_duration(activity.get("duration", ""), start_time)
        
        # Build the JSON-LD structure
        json_ld = {
            "@context": "https://schema.org",
            "@type": "ExerciseAction",
            "identifier": activity.get("activityId", ""),
            "exerciseType": activity.get("sport", ""),
            "startTime": start_time,
            "endTime": end_time,
            "distance": activity.get("distance", ""),
            "duration": activity.get("duration", ""),
            "elevationGain": activity.get("elevation", ""),
            "pace": activity.get("pace", ""),
            "calories": activity.get("calories", ""),
            "averageHeartRate": activity.get("averageHeartRate", ""),
            "weather": activity.get("weather", {}),
            "laps": activity.get("laps", [])
        }
        
        # Add enhanced Garmin-specific fields if present
        if activity.get("runningDynamics"):
            json_ld["runningDynamics"] = activity["runningDynamics"]
        
        if activity.get("sleepData"):
            json_ld["sleepData"] = activity["sleepData"]
        
        if activity.get("wellness"):
            json_ld["wellness"] = activity["wellness"]
        
        # Format the markdown
        distance = activity.get("distance", "")
        duration = activity.get("duration", "")
        pace = activity.get("pace", "")
        
        title_parts = [
            activity.get("workoutName", "Activity"),
            f"({distance}, {duration}" + (f", {pace}" if pace else "") + ")"
        ]
        
        title = f"### {activity.get('date', '')} — {' '.join(title_parts)}"
        
        markdown = f"""
{title}

```jsonld
{json.dumps(json_ld, indent=2)}
```
"""
        return markdown

    def ensure_proper_sorting(self):
        """Sort all activities in index.md by ID (newest first)"""
        try:
            content = self.index_path.read_text()
            
            # Split into activity blocks
            blocks = re.split(r'(?=### )', content)
            
            # Find header (everything before first activity)
            header = ""
            activity_blocks = []
            
            for block in blocks:
                if block.strip():
                    if block.startswith('### '):
                        activity_blocks.append(block)
                    else:
                        header += block
            
            # Extract IDs and sort
            blocks_with_ids = []
            for block in activity_blocks:
                id_match = re.search(r'"identifier": "(\d+)"', block)
                if id_match:
                    activity_id = int(id_match.group(1))
                    blocks_with_ids.append((activity_id, block))
            
            # Sort by ID descending (newest first)
            blocks_with_ids.sort(key=lambda x: x[0], reverse=True)
            
            # Reconstruct file
            sorted_content = header + ''.join(block[1] for block in blocks_with_ids)
            
            self.index_path.write_text(sorted_content)
            logger.info(f"Ensured {len(blocks_with_ids)} activities are properly sorted by ID")
            
        except Exception as e:
            logger.warning(f"Could not sort index.md: {e}")

    def render_feed(self):
        """Main rendering function"""
        logger.info("Starting feed render process...")
        
        # Read activities from scraper output
        try:
            with open(self.activities_path, 'r') as f:
                activities = json.load(f)
        except FileNotFoundError:
            logger.error("activities.json not found. Did the scraper run correctly?")
            return
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in activities.json: {e}")
            return
        
        if not activities:
            logger.info("No new activities to render. Ensuring proper sorting...")
            self.ensure_proper_sorting()
            return
        
        logger.info(f"Processing {len(activities)} activities")
        
        # Get existing IDs to avoid duplicates
        existing_ids = self.get_existing_ids()
        
        # Also get existing datetime signatures for Strava->Garmin transition
        existing_signatures = self.get_existing_datetime_signatures()
        
        # Read existing content
        try:
            existing_content = self.index_path.read_text()
        except FileNotFoundError:
            existing_content = ""
        
        # Separate new activities from potential upgrades/duplicates
        new_activities = []
        potential_upgrades = []
        skipped_duplicates = []
        
        for activity in activities:
            activity_id = activity.get("activityId")
            
            # Check for ID-based duplicates
            if activity_id in existing_ids:
                potential_upgrades.append(activity)
                continue
            
            # Check for datetime signature duplicates (Strava->Garmin transition)
            signature = self.create_datetime_signature(activity)
            if signature and signature in existing_signatures:
                logger.info(f"Skipping Garmin activity {activity_id} - matches existing activity by datetime signature: {signature}")
                skipped_duplicates.append(activity)
                continue
            
            new_activities.append(activity)
        
        if skipped_duplicates:
            logger.info(f"Skipped {len(skipped_duplicates)} duplicate activities based on datetime matching")
        
        # Handle upgrades (activities with enhanced data)
        upgrades_count = 0
        for activity in potential_upgrades:
            # Check if this is an upgrade with new data
            has_enhanced_data = any([
                activity.get("runningDynamics"),
                activity.get("sleepData"),
                activity.get("wellness"),
                activity.get("weather", {}) != {},
                activity.get("laps", []) != []
            ])
            
            if has_enhanced_data:
                logger.info(f"Upgrading activity {activity['activityId']} with enhanced data")
                new_markdown = self.to_markdown(activity)
                
                # Replace the old block with the new one
                pattern = rf'### [\s\S]*?"identifier": "{re.escape(activity["activityId"])}"[\s\S]*?```\n'
                existing_content = re.sub(pattern, new_markdown, existing_content)
                upgrades_count += 1
        
        if upgrades_count > 0:
            logger.info(f"Upgraded {upgrades_count} existing activities with enhanced data")
        
        # Handle new activities
        if new_activities:
            logger.info(f"Adding {len(new_activities)} new activities")
            
            # Sort new activities by ID (newest first)
            new_activities.sort(key=lambda x: int(x.get("activityId", "0")), reverse=True)
            
            # Convert to markdown
            new_content = ''.join(self.to_markdown(activity) for activity in new_activities)
            
            # Prepend to existing content
            existing_content = new_content + existing_content
        
        # Write updated content
        self.index_path.write_text(existing_content)
        
        # Update last_id.json with newest activity
        if activities:
            newest_activity = max(activities, key=lambda x: int(x.get("activityId", "0")))
            self.update_last_id(newest_activity)
        
        # Ensure proper sorting
        self.ensure_proper_sorting()
        
        logger.info("Feed render process completed")

def main():
    """Main entry point"""
    try:
        renderer = GarminRenderer()
        renderer.render_feed()
    except Exception as e:
        logger.error(f"Render failed: {e}")
        exit(1)

if __name__ == "__main__":
    main() 