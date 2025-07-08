#!/usr/bin/env python3

import os
import yaml
import json
from datetime import datetime
import re

def fix_step_calculation(data):
    """Fix unrealistic step counts with better calculation"""
    workouts = data.get('workout_metrics', [])
    
    # Calculate workout steps (roughly 1,900 steps per mile for running)
    workout_steps = 0
    for workout in workouts:
        distance = workout.get('distance_mi', 0)
        if workout.get('type') == 'Run':
            workout_steps += int(distance * 1900)  # More realistic for running
        else:
            workout_steps += int(distance * 1800)  # For other activities
    
    # Add baseline daily steps (estimated 6,000-8,000 for non-workout activity)
    baseline_steps = 7000
    
    # Total realistic daily steps
    realistic_total = workout_steps + baseline_steps
    
    return realistic_total

def format_splits_better(splits):
    """Create better formatted splits section that works across markdown renderers"""
    if not splits:
        return "No splits data available"
    
    content = []
    content.append("**Mile-by-Mile Breakdown:**")
    content.append("")
    
    for split in splits:
        mile = split.get('mile', '?')
        
        # Time formatting
        time_s = split.get('mile_time_s', 0)
        if time_s > 0:
            minutes = time_s // 60
            seconds = time_s % 60
            time_str = f"{minutes}:{seconds:02d}"
        else:
            time_str = "N/A"
        
        # Pace formatting
        pace_s = split.get('avg_pace_s_per_mi', 0)
        if pace_s > 0:
            pace_min = pace_s // 60
            pace_sec = pace_s % 60
            pace_str = f"{pace_min}:{pace_sec:02d}/mi"
        else:
            pace_str = "N/A"
        
        # Heart rate
        avg_hr = split.get('avg_hr', 0)
        max_hr = split.get('max_hr', 0)
        if avg_hr > 0:
            hr_str = f"{avg_hr} bpm avg"
            if max_hr > avg_hr:
                hr_str += f" ({max_hr} max)"
        else:
            hr_str = "N/A"
        
        # Elevation
        elev = split.get('elev_gain_ft', 0)
        if elev != 0:
            elev_str = f"{elev:+d} ft"
        else:
            elev_str = "0 ft"
        
        # Format as list item for better compatibility
        content.append(f"• **Mile {mile}:** {time_str} • {pace_str} • {hr_str} • {elev_str}")
    
    return '\n'.join(content)

def process_daily_file(filepath):
    """Process a single daily markdown file to fix steps and formatting"""
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
    
    # Fix step count
    old_steps = data.get('daily_metrics', {}).get('steps', 0)
    new_steps = fix_step_calculation(data)
    
    # Update YAML data
    if 'daily_metrics' in data:
        data['daily_metrics']['steps'] = new_steps
    
    # Fix markdown content - update step display
    markdown_content = re.sub(
        r'\*\*Steps:\*\* [\d,]+',
        f'**Steps:** {new_steps:,}',
        markdown_content
    )
    
    # Update the totals line
    markdown_content = re.sub(
        r'(\*\*Totals:\*\* [^•]+• [^•]+• [^•]+• )[\d,]+( steps)',
        f'\\g<1>{new_steps:,}\\g<2>',
        markdown_content
    )
    
    # Fix splits formatting - replace table with better format
    splits_pattern = r'\*\*Splits:\*\*\n\| Mile.*?\n(?:\|.*?\n)*'
    match = re.search(splits_pattern, markdown_content, re.DOTALL)
    
    if match:
        # Get splits data from YAML
        workouts = data.get('workout_metrics', [])
        if workouts and workouts[0].get('splits'):
            new_splits_content = format_splits_better(workouts[0]['splits'])
            markdown_content = markdown_content[:match.start()] + f"**Splits:**\n{new_splits_content}\n" + markdown_content[match.end():]
    
    # Update YAML front matter
    updated_yaml = yaml.dump(data, default_flow_style=False, sort_keys=False)
    
    # Update JSON section
    json_pattern = r'(```json\n)({.*?})\n(```)'
    json_match = re.search(json_pattern, markdown_content, re.DOTALL)
    if json_match:
        # Update JSON with new step count
        try:
            json_data = json.loads(json_match.group(2))
            if 'daily_metrics' in json_data:
                json_data['daily_metrics']['steps'] = new_steps
            
            updated_json = json.dumps(json_data, indent=2)
            markdown_content = markdown_content[:json_match.start()] + f"{json_match.group(1)}{updated_json}\n{json_match.group(3)}" + markdown_content[json_match.end():]
        except json.JSONDecodeError:
            print(f"Warning: Could not parse JSON in {filepath}")
    
    # Write updated content
    updated_content = f"---\n{updated_yaml}---\n{markdown_content}"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"Updated {filepath}: {old_steps:,} → {new_steps:,} steps")

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