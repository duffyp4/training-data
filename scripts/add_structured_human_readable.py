#!/usr/bin/env python3

import os
import yaml
import json
from datetime import datetime
import re

def format_time(seconds):
    """Convert seconds to human readable time format"""
    if seconds is None:
        return "N/A"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}m {secs}s"
    else:
        return f"{secs}s"

def format_pace(pace_seconds_per_mile):
    """Convert pace in seconds per mile to mm:ss format"""
    if pace_seconds_per_mile is None:
        return "N/A"
    
    minutes = pace_seconds_per_mile // 60
    seconds = pace_seconds_per_mile % 60
    return f"{minutes}:{seconds:02d}/mi"

def format_hr_zone(avg_hr, max_hr):
    """Format heart rate display"""
    if avg_hr is None and max_hr is None:
        return "N/A"
    elif avg_hr is None:
        return f"Max: {max_hr} bpm"
    elif max_hr is None:
        return f"Avg: {avg_hr} bpm"
    else:
        return f"Avg: {avg_hr} bpm, Max: {max_hr} bpm"

def generate_structured_readable(data):
    """Generate structured human-readable content"""
    content = []
    
    # Sleep Metrics Section
    content.append("## Sleep Metrics")
    sleep = data.get('sleep_metrics', {})
    if any(v is not None for v in sleep.values()):
        if sleep.get('sleep_minutes'):
            hours = sleep['sleep_minutes'] // 60
            mins = sleep['sleep_minutes'] % 60
            content.append(f"**Total Sleep:** {hours}h {mins}m")
        
        if sleep.get('deep_minutes') or sleep.get('light_minutes') or sleep.get('rem_minutes'):
            stages = []
            if sleep.get('deep_minutes'):
                stages.append(f"Deep: {sleep['deep_minutes']}m")
            if sleep.get('light_minutes'):
                stages.append(f"Light: {sleep['light_minutes']}m")
            if sleep.get('rem_minutes'):
                stages.append(f"REM: {sleep['rem_minutes']}m")
            if sleep.get('awake_minutes'):
                stages.append(f"Awake: {sleep['awake_minutes']}m")
            content.append(f"**Sleep Stages:** {' • '.join(stages)}")
        
        if sleep.get('sleep_score'):
            content.append(f"**Sleep Score:** {sleep['sleep_score']}")
        
        recovery_metrics = []
        if sleep.get('resting_hr'):
            recovery_metrics.append(f"RHR: {sleep['resting_hr']} bpm")
        if sleep.get('hrv_night_avg'):
            recovery_metrics.append(f"HRV: {sleep['hrv_night_avg']} ms")
        if recovery_metrics:
            content.append(f"**Recovery:** {' • '.join(recovery_metrics)}")
    else:
        content.append("No sleep data available for this date")
    
    content.append("")  # Empty line
    
    # Daily Metrics Section
    content.append("## Daily Metrics")
    daily = data.get('daily_metrics', {})
    
    # Body Battery
    bb = daily.get('body_battery', {})
    if bb.get('charge') is not None or bb.get('drain') is not None:
        bb_info = []
        if bb.get('charge'):
            bb_info.append(f"Charged: +{bb['charge']}")
        if bb.get('drain'):
            bb_info.append(f"Drained: -{bb['drain']}")
        content.append(f"**Body Battery:** {' • '.join(bb_info)}")
    
    # Steps and activity
    if daily.get('steps'):
        content.append(f"**Steps:** {daily['steps']:,}")
    
    # Daily totals
    totals = []
    if daily.get('total_workout_distance_mi'):
        totals.append(f"{daily['total_workout_distance_mi']:.1f} mi")
    if daily.get('total_moving_time_s'):
        totals.append(format_time(daily['total_moving_time_s']))
    if daily.get('total_elev_gain_ft'):
        totals.append(f"{daily['total_elev_gain_ft']} ft ↑")
    
    if totals:
        content.append(f"**Workout Totals:** {' • '.join(totals)}")
    
    content.append("")  # Empty line
    
    # Workout Details Section
    workouts = data.get('workout_metrics', [])
    if workouts:
        content.append("## Workout Details")
        
        for i, workout in enumerate(workouts):
            if len(workouts) > 1:
                content.append(f"### Workout {i+1}: {workout.get('type', 'Unknown')}")
            else:
                content.append(f"### {workout.get('type', 'Unknown')}")
            
            # Basic workout info
            workout_info = []
            if workout.get('distance_mi'):
                workout_info.append(f"{workout['distance_mi']:.2f} mi")
            if workout.get('moving_time_s'):
                workout_info.append(format_time(workout['moving_time_s']))
            if workout.get('elev_gain_ft'):
                workout_info.append(f"{workout['elev_gain_ft']} ft ↑")
            
            if workout_info:
                content.append(f"**Distance & Time:** {' • '.join(workout_info)}")
            
            # Heart rate
            hr_info = format_hr_zone(workout.get('avg_hr'), workout.get('max_hr'))
            if hr_info != "N/A":
                content.append(f"**Heart Rate:** {hr_info}")
            
            # Pace
            if workout.get('avg_pace_s_per_mi'):
                content.append(f"**Average Pace:** {format_pace(workout['avg_pace_s_per_mi'])}")
            
            # Splits
            splits = workout.get('splits', [])
            if splits:
                content.append("")
                content.append("**Splits:**")
                content.append("| Mile | Time | Pace | HR | Elev |")
                content.append("|------|------|------|----|----- |")
                
                for split in splits:
                    mile = split.get('mile', '?')
                    time = format_time(split.get('mile_time_s')) if split.get('mile_time_s') else "N/A"
                    pace = format_pace(split.get('avg_pace_s_per_mi')) if split.get('avg_pace_s_per_mi') else "N/A"
                    hr = format_hr_zone(split.get('avg_hr'), split.get('max_hr'))
                    elev = f"{split.get('elev_gain_ft', 0)} ft" if split.get('elev_gain_ft') is not None else "N/A"
                    
                    content.append(f"| {mile} | {time} | {pace} | {hr} | {elev} |")
            
            content.append("")  # Empty line between workouts
    
    return '\n'.join(content)

def process_daily_file(filepath):
    """Process a single daily markdown file"""
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
    
    # Generate structured readable content
    structured_content = generate_structured_readable(data)
    
    # Find where to insert the structured content (before "Full JSON")
    full_json_pattern = r'<details>\s*\n<summary>Full JSON</summary>'
    match = re.search(full_json_pattern, markdown_content)
    
    if match:
        # Insert structured content before Full JSON
        before_json = markdown_content[:match.start()]
        json_section = markdown_content[match.start():]
        
        # Remove any existing structured content if present
        # Look for content between basic summary and Full JSON
        lines = before_json.strip().split('\n')
        
        # Find the basic summary line (should contain "Totals:" and "Sleep:")
        summary_end_idx = -1
        for i, line in enumerate(lines):
            if line.startswith('**Sleep:**') or 'Sleep:' in line:
                summary_end_idx = i
                break
        
        if summary_end_idx >= 0:
            # Keep everything up to and including the sleep line
            before_structured = '\n'.join(lines[:summary_end_idx + 1])
            
            # Add the new structured content
            new_markdown = f"{before_structured}\n\n{structured_content}\n\n{json_section}"
        else:
            # If we can't find the basic summary, just add before JSON
            new_markdown = f"{before_json.strip()}\n\n{structured_content}\n\n{json_section}"
    else:
        print(f"Warning: Could not find Full JSON section in {filepath}")
        return
    
    # Write updated content
    updated_content = f"---\n{yaml_front_matter}---\n{new_markdown}"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"Updated {filepath}")

def main():
    """Process all daily markdown files"""
    data_dir = 'data'
    
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.md') and file != 'index.md':
                filepath = os.path.join(root, file)
                try:
                    process_daily_file(filepath)
                except Exception as e:
                    print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    main() 