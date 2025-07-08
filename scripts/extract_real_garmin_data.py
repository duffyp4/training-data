#!/usr/bin/env python3
"""
Extract Real Garmin Workout Data Only
Remove fabricated wellness data, keep authentic workout measurements
"""

import yaml
import json
from pathlib import Path

def extract_real_workout_data(file_path):
    """Extract only real workout data, discard fabricated wellness"""
    content = file_path.read_text()
    
    # Split front matter and content
    if not content.startswith('---'):
        return None
    
    parts = content.split('---', 2)
    if len(parts) < 3:
        return None
    
    try:
        data = yaml.safe_load(parts[1])
    except:
        return None
    
    # Extract only real workout data
    real_workouts = []
    workout_metrics = data.get('workout_metrics', [])
    
    for workout in workout_metrics:
        # Keep only authentic workout measurements
        real_workout = {}
        
        # Real GPS/device data
        real_fields = [
            'id', 'type', 'start', 'distance_mi', 'moving_time_s', 
            'elev_gain_ft', 'avg_hr', 'max_hr', 'avg_pace_s_per_mi', 'calories'
        ]
        
        for field in real_fields:
            if field in workout:
                real_workout[field] = workout[field]
        
        # Real splits data (from Garmin API)
        splits = workout.get('splits', [])
        if splits:
            real_splits = []
            for split in splits:
                real_split = {}
                # Keep only measured split data
                split_fields = [
                    'mile', 'avg_hr', 'max_hr', 'avg_pace_s_per_mi', 
                    'mile_time_s', 'elev_gain_ft'
                ]
                
                for field in split_fields:
                    if field in split and split[field] not in [None, 0, ""]:
                        real_split[field] = split[field]
                
                if real_split:
                    real_splits.append(real_split)
            
            if real_splits:
                real_workout['splits'] = real_splits
        
        if real_workout:
            real_workouts.append(real_workout)
    
    return real_workouts

def process_july_files():
    """Process July files to extract real data only"""
    july_dir = Path("data/2025/07")
    
    if not july_dir.exists():
        print("July directory not found")
        return
    
    for md_file in july_dir.glob("*.md"):
        if md_file.name == "README.md":
            continue
            
        print(f"Processing {md_file}")
        
        real_workouts = extract_real_workout_data(md_file)
        if not real_workouts:
            continue
        
        # Calculate totals from real data
        total_distance = sum(w.get('distance_mi', 0) for w in real_workouts)
        total_time = sum(w.get('moving_time_s', 0) for w in real_workouts)
        total_elevation = sum(w.get('elev_gain_ft', 0) for w in real_workouts)
        total_calories = sum(w.get('calories', 0) for w in real_workouts)
        
        # Create clean data structure
        date = md_file.stem.zfill(2)  # "07" -> "07"
        full_date = f"2025-07-{date}"
        
        clean_data = {
            "date": full_date,
            "schema": 3,  # Real-data-only schema
            "summary": {
                "workouts": len(real_workouts),
                "total_distance_mi": round(total_distance, 2),
                "total_time_s": total_time,
                "total_elevation_ft": total_elevation,
                "total_calories": total_calories
            },
            "workouts": real_workouts
        }
        
        # Generate new content
        yaml_str = yaml.dump(clean_data, default_flow_style=False, sort_keys=False)
        
        hours = total_time // 3600
        minutes = (total_time % 3600) // 60
        
        new_content = f"""---
{yaml_str}---
# {full_date} · Training Data (Real Data Only)
**{len(real_workouts)} workout{'s' if len(real_workouts) != 1 else ''} • {total_distance:.1f} mi • {hours}h {minutes}m • {total_elevation} ft ↑ • {total_calories} cal**

*Real Garmin workout data with authentic splits. No fabricated wellness data.*

<details>
<summary>Full Data</summary>

```json
{json.dumps(clean_data, indent=2)}
```
</details>
"""
        
        # Write clean file
        md_file.write_text(new_content)
        print(f"✅ Cleaned {md_file} - removed fake wellness data, kept real workout metrics")

if __name__ == "__main__":
    process_july_files() 