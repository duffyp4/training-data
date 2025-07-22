#!/usr/bin/env python3
"""
Generate Index
Scans the data directory and creates an index.md file with links to all existing daily files
"""

import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_data_from_file(file_path: Path) -> Dict:
    """Extract basic data from a daily file"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract YAML front matter
        if content.startswith('---'):
            end_yaml = content.find('---', 3)
            if end_yaml != -1:
                yaml_content = content[3:end_yaml]
                data = yaml.safe_load(yaml_content)
                
                # Calculate totals from workout_metrics
                workouts = data.get('workout_metrics', [])
                total_distance = sum(w.get('distance_mi', 0) for w in workouts)
                workout_count = len(workouts)
                
                return {
                    'date': data.get('date'),
                    'workout_count': workout_count,
                    'total_distance': total_distance,
                    'file_path': str(file_path)
                }
    except Exception as e:
        logger.warning(f"Could not parse {file_path}: {e}")
    
    return None

def format_date_display(date_str: str) -> str:
    """Convert YYYY-MM-DD to readable format"""
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return dt.strftime('%A, %B %d, %Y')
    except:
        return date_str

def generate_index():
    """Generate index.md from existing data files"""
    data_dir = Path('data')
    
    # Find all daily files
    daily_files = []
    for year_dir in sorted(data_dir.glob('20*')):
        if year_dir.is_dir():
            for month_dir in sorted(year_dir.glob('*')):
                if month_dir.is_dir():
                    for day_file in sorted(month_dir.glob('*.md')):
                        file_data = extract_data_from_file(day_file)
                        if file_data:
                            daily_files.append(file_data)
    
    # Sort by date (newest first)
    daily_files.sort(key=lambda x: x['date'], reverse=True)
    
    logger.info(f"Found {len(daily_files)} daily files")
    
    # Generate index content
    content = []
    content.append("# Training Data")
    content.append("")
    content.append("This repository contains comprehensive training data with detailed per-split metrics, workout data, and wellness information in structured daily files.")
    content.append("")
    content.append("## Recent Activities")
    content.append("")
    
    # Show recent activities (top 15)
    recent_files = daily_files[:15]
    for file_data in recent_files:
        date_display = format_date_display(file_data['date'])
        workout_text = "workout" if file_data['workout_count'] == 1 else "workouts"
        distance_text = f"{file_data['total_distance']:.1f} miles" if file_data['total_distance'] > 0 else "0 miles"
        
        link_path = file_data['file_path'].replace('\\', '/')  # Ensure forward slashes
        content.append(f"- **[{date_display}]({link_path})** - {file_data['workout_count']} {workout_text}, {distance_text}")
    
    content.append("")
    content.append("## Complete Data Index")
    content.append("")
    
    if len(daily_files) > 15:
        content.append(f"**All {len(daily_files)} daily files:** ")
        content.append("")
        
        # Group by month for better organization
        months = {}
        for file_data in daily_files:
            date_obj = datetime.strptime(file_data['date'], '%Y-%m-%d')
            month_key = date_obj.strftime('%Y-%m')
            month_display = date_obj.strftime('%B %Y')
            
            if month_key not in months:
                months[month_key] = {
                    'display': month_display,
                    'files': []
                }
            months[month_key]['files'].append(file_data)
        
        # Display by month (newest first)
        for month_key in sorted(months.keys(), reverse=True):
            month_data = months[month_key]
            content.append(f"### {month_data['display']}")
            content.append("")
            
            for file_data in sorted(month_data['files'], key=lambda x: x['date'], reverse=True):
                date_display = format_date_display(file_data['date'])
                workout_text = "workout" if file_data['workout_count'] == 1 else "workouts"
                distance_text = f"{file_data['total_distance']:.1f} miles" if file_data['total_distance'] > 0 else "0 miles"
                
                link_path = file_data['file_path'].replace('\\', '/')
                content.append(f"- **[{date_display}]({link_path})** - {file_data['workout_count']} {workout_text}, {distance_text}")
            
            content.append("")
    
    # Summary statistics
    total_workouts = sum(f['workout_count'] for f in daily_files)
    total_distance = sum(f['total_distance'] for f in daily_files)
    date_range_start = daily_files[-1]['date'] if daily_files else "N/A"
    date_range_end = daily_files[0]['date'] if daily_files else "N/A"
    
    content.append("## Summary")
    content.append("")
    content.append(f"- **Total Files:** {len(daily_files)} daily training files")
    content.append(f"- **Date Range:** {format_date_display(date_range_start)} to {format_date_display(date_range_end)}")
    content.append(f"- **Total Workouts:** {total_workouts}")
    content.append(f"- **Total Distance:** {total_distance:.1f} miles")
    content.append("")
    content.append("Each daily file contains YAML front matter, human-readable summaries, detailed workout splits, and complete JSON data.")
    content.append("")
    
    # Write index.md
    index_content = '\n'.join(content)
    with open('index.md', 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    # Write data/index.json for AI agent consumption
    # Added 2025-07-22: AI agents were unable to discover recent training data 
    # because index.json was stale (only went to July 7th vs July 21st actual data)
    json_data = []
    for file_data in daily_files:
        json_data.append({
            "date": file_data['date'],
            "path": file_data['file_path'].replace('\\', '/')
        })
    
    data_dir = Path('data')
    data_dir.mkdir(exist_ok=True)
    
    with open(data_dir / 'index.json', 'w', encoding='utf-8') as f:
        import json
        json.dump(json_data, f, indent=2)
    
    logger.info("Generated index.md and data/index.json successfully")
    return len(daily_files)

def main():
    """Main entry point"""
    try:
        file_count = generate_index()
        print(f"✅ Generated index.md with {file_count} daily files")
    except Exception as e:
        logger.error(f"Error generating index: {e}")
        exit(1)

if __name__ == "__main__":
    main() 