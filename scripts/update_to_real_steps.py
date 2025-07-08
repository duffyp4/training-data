#!/usr/bin/env python3

import os
import yaml
import json
import sys
from pathlib import Path
from datetime import datetime
import logging
import re

# Add the scripts directory to path to import garmin_scraper
sys.path.append(str(Path(__file__).parent))

# Load environment variables from .env file
def load_env_file():
    env_path = Path('.env')
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key] = value

load_env_file()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_real_steps_from_garmin(date_str):
    """Get real step data from Garmin for a specific date"""
    try:
        from garmin_scraper import GarminScraper
        scraper = GarminScraper()
        
        # Authenticate with Garmin Connect
        if not scraper.authenticate():
            logger.warning(f"Failed to authenticate with Garmin Connect for {date_str}")
            return None
        
        # Get wellness data which now includes steps
        wellness_data = scraper.get_wellness_data(date_str)
        
        if wellness_data and wellness_data.get('dailySteps'):
            return wellness_data['dailySteps']
        
        return None
        
    except Exception as e:
        logger.warning(f"Error getting step data for {date_str}: {e}")
        return None

def update_file_with_real_steps(filepath):
    """Update a single daily file with real step data from Garmin"""
    print(f"Processing {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Split content into sections
    if '---\n' in content:
        parts = content.split('---\n', 2)
        if len(parts) >= 3:
            yaml_front_matter = parts[1]
            markdown_content = parts[2]
        else:
            print(f"Warning: Could not parse YAML front matter in {filepath}")
            return
    else:
        print(f"Warning: No YAML front matter found in {filepath}")
        return
    
    # Parse YAML data
    try:
        data = yaml.safe_load(yaml_front_matter)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML in {filepath}: {e}")
        return
    
    # Extract date from the data
    date_str = data.get('date')
    if not date_str:
        print(f"Warning: No date found in {filepath}")
        return
    
    # Get real step data from Garmin
    real_steps = get_real_steps_from_garmin(date_str)
    
    if real_steps is None:
        print(f"Could not get real step data for {date_str}, keeping existing value")
        return
    
    # Update step count in YAML data
    old_steps = data.get('daily_metrics', {}).get('steps', 0)
    data['daily_metrics']['steps'] = real_steps
    
    # Update markdown content - update step display
    markdown_content = re.sub(
        r'\*\*Steps:\*\* [\d,]+',
        f'**Steps:** {real_steps:,}',
        markdown_content
    )
    
    # Update the totals line
    markdown_content = re.sub(
        r'(\*\*Totals:\*\* [^•]+• [^•]+• [^•]+• )[\d,]+( steps)',
        f'\\g<1>{real_steps:,}\\g<2>',
        markdown_content
    )
    
    # Update YAML front matter
    updated_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False)
    
    # Update JSON section
    json_pattern = r'(```json\n)({.*?})\n(```)'
    json_match = re.search(json_pattern, markdown_content, re.DOTALL)
    if json_match:
        try:
            json_data = json.loads(json_match.group(2))
            if 'daily_metrics' in json_data:
                json_data['daily_metrics']['steps'] = real_steps
            
            updated_json = json.dumps(json_data, indent=2)
            markdown_content = markdown_content[:json_match.start()] + f"{json_match.group(1)}{updated_json}\n{json_match.group(3)}" + markdown_content[json_match.end():]
        except json.JSONDecodeError:
            print(f"Warning: Could not parse JSON in {filepath}")
    
    # Write updated content
    updated_content = f"---\n{updated_yaml}---\n{markdown_content}"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"Updated {filepath}: {old_steps:,} → {real_steps:,} steps (real Garmin data)")

def main():
    """Process all daily markdown files to get real step data"""
    data_dir = 'data'
    
    # Process files in chronological order to avoid rate limiting issues
    files_to_process = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.md') and file != 'index.md':
                filepath = os.path.join(root, file)
                files_to_process.append(filepath)
    
    # Sort files to process in date order
    files_to_process.sort()
    
    print(f"Found {len(files_to_process)} files to process")
    
    for i, filepath in enumerate(files_to_process):
        try:
            print(f"Processing file {i+1}/{len(files_to_process)}")
            update_file_with_real_steps(filepath)
            
            # Add a small delay to avoid overwhelming Garmin API
            import time
            time.sleep(1)
            
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    main() 