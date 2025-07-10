#!/usr/bin/env python3
"""
Garmin to Daily Files Converter
Converts activities.json from garmin_scraper to structured daily files in data/YYYY/MM/DD.md format
Uses the multipage design with YAML front matter, human-readable sections, and expandable JSON
Enhanced with FIT file data: training effects, HR zones, location, and per-split running dynamics
"""

import json
import os
import yaml
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import re

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GarminToDailyFiles:
    def __init__(self):
        self.data_dir = Path("data")
        self.activities_path = Path("activities.json")
        self.last_id_file = self.data_dir / "last_id.json"
        
        # Ensure data directory exists
        self.data_dir.mkdir(exist_ok=True)

    def convert_old_activities_to_new_format(self, activities: List[Dict]) -> Dict[str, Dict]:
        """Convert activities.json format to new daily file structure"""
        daily_data = {}
        
        for activity in activities:
            # Extract date from activity
            date_str = self.extract_date_from_activity(activity)
            if not date_str:
                continue
                
            # Initialize daily data structure if needed
            if date_str not in daily_data:
                daily_data[date_str] = {
                    "date": date_str,
                    "schema": 2,
                    "sleep_metrics": {
                        "sleep_minutes": None,
                        "deep_minutes": None,
                        "light_minutes": None,
                        "rem_minutes": None,
                        "awake_minutes": None,
                        "sleep_score": None,
                        "hrv_night_avg": None
                    },
                    "daily_metrics": {
                        "body_battery": {
                            "charge": None,
                            "drain": None
                        },
                        "steps": None,
                        "resting_hr": None  # Moved from sleep_metrics
                    },
                    "workout_metrics": []
                    # Note: Removed self_evaluation section per user request
                }
            
            # Process sleep data if available
            if activity.get('sleepData'):
                sleep_data = activity['sleepData']
                daily_data[date_str]['sleep_metrics'].update({
                    "sleep_minutes": self.parse_duration_to_minutes(sleep_data.get('totalSleep')),
                    "deep_minutes": self.parse_duration_to_minutes(sleep_data.get('deepSleep')),
                    "light_minutes": self.parse_duration_to_minutes(sleep_data.get('lightSleep')),
                    "rem_minutes": self.parse_duration_to_minutes(sleep_data.get('remSleep')),
                    "awake_minutes": self.parse_duration_to_minutes(sleep_data.get('awakeTime')),
                    "sleep_score": sleep_data.get('sleepScore')
                })
            
            # Process wellness data if available
            if activity.get('wellness'):
                wellness = activity['wellness']
                daily_data[date_str]['daily_metrics'].update({
                    "steps": wellness.get('dailySteps'),
                    "resting_hr": wellness.get('restingHeartRate')
                })
                
                if wellness.get('bodyBattery'):
                    daily_data[date_str]['daily_metrics']['body_battery'] = wellness['bodyBattery']
                
                if wellness.get('hrv'):
                    daily_data[date_str]['sleep_metrics']['hrv_night_avg'] = wellness['hrv']
                
                # Add lactate threshold (NEW)
                if wellness.get('lactateThreshold'):
                    daily_data[date_str]['daily_metrics']['lactate_threshold'] = wellness['lactateThreshold']
            
            # Process workout data
            workout_data = self.convert_activity_to_workout_metrics(activity)
            if workout_data:
                daily_data[date_str]['workout_metrics'].append(workout_data)
        
        return daily_data

    def extract_date_from_activity(self, activity: Dict) -> Optional[str]:
        """Extract date in YYYY-MM-DD format from activity"""
        try:
            # Try startTime first (ISO format)
            if activity.get('startTime'):
                dt = datetime.fromisoformat(activity['startTime'].replace('Z', '+00:00'))
                return dt.strftime('%Y-%m-%d')
            
            # Fallback to date field parsing
            if activity.get('date'):
                date_str = activity['date']
                if ',' in date_str:
                    date_part = date_str.split(',')[1].strip()
                    dt = datetime.strptime(date_part, "%m/%d/%Y")
                    return dt.strftime('%Y-%m-%d')
                    
        except Exception as e:
            logger.warning(f"Could not parse date from activity: {e}")
        
        return None

    def parse_duration_to_minutes(self, duration_str: Optional[str]) -> Optional[int]:
        """Convert duration string like '7h 30m' to minutes"""
        if not duration_str:
            return None
        
        try:
            total_minutes = 0
            # Parse hours
            if 'h' in duration_str:
                hours = int(duration_str.split('h')[0])
                total_minutes += hours * 60
            
            # Parse minutes
            if 'm' in duration_str:
                minutes_part = duration_str.split('h')[-1] if 'h' in duration_str else duration_str
                minutes = int(minutes_part.split('m')[0].strip())
                total_minutes += minutes
            
            return total_minutes if total_minutes > 0 else None
        except Exception:
            return None

    def convert_activity_to_workout_metrics(self, activity: Dict) -> Optional[Dict]:
        """Convert activity to workout_metrics format with enhanced FIT data"""
        try:
            # Parse distance
            distance_str = activity.get('distance', '')
            distance_mi = 0
            if distance_str and 'mi' in distance_str:
                distance_mi = float(distance_str.replace('mi', '').strip())
            
            # Parse duration to seconds
            duration_str = activity.get('duration', '')
            moving_time_s = self.parse_duration_to_seconds(duration_str)
            
            # Parse elevation
            elevation_str = activity.get('elevation', '')
            elev_gain_ft = 0
            if elevation_str and 'ft' in elevation_str:
                elev_gain_ft = int(elevation_str.replace('ft', '').strip())
            
            # Parse heart rate
            avg_hr = None
            max_hr = None
            avg_hr_str = activity.get('averageHeartRate', '')
            if 'bpm' in avg_hr_str:
                avg_hr = int(avg_hr_str.replace('bpm', '').strip())
            
            max_hr_str = activity.get('maxHeartRate', '')
            if 'bpm' in max_hr_str:
                max_hr = int(max_hr_str.replace('bpm', '').strip())
            
            # Parse pace to seconds per mile
            pace_str = activity.get('pace', '')
            avg_pace_s_per_mi = self.parse_pace_to_seconds(pace_str)
            
            workout = {
                "id": int(activity.get('activityId', 0)),
                "type": activity.get('sport', 'Unknown'),
                "start": activity.get('startTime'),
                "distance_mi": distance_mi,
                "moving_time_s": moving_time_s,
                "elev_gain_ft": elev_gain_ft,
                "avg_hr": avg_hr,
                "max_hr": max_hr,
                "avg_pace_s_per_mi": avg_pace_s_per_mi,
                "splits": self.convert_laps_to_splits(activity.get('laps', []))
            }
            
            # Add enhanced data from API responses
            if activity.get('location'):
                if isinstance(activity['location'], dict) and activity['location'].get('city'):
                    workout["location"] = activity['location']['city']
                else:
                    workout["location"] = activity['location']
            
            # Add Visual Crossing weather data
            if activity.get('weather'):
                workout["weather"] = activity['weather']
            
            # Add training effects from API
            if activity.get('training_effects'):
                workout["training_effects"] = activity['training_effects']
            
            # Add running dynamics from API
            if activity.get('running_dynamics'):
                workout["running_dynamics"] = activity['running_dynamics']
            
            # Add HR zones from API (NEW - replaces power zones)
            if activity.get('hr_zones'):
                workout["hr_zones"] = activity['hr_zones']
            elif activity.get('power_zones'):
                # Fallback to power zones if HR zones not available
                workout["power_zones"] = activity['power_zones']
            
            # Add power data from API
            if activity.get('power'):
                workout["power"] = activity['power']
            
            return workout
            
        except Exception as e:
            logger.warning(f"Could not convert activity to workout metrics: {e}")
            return None

    def parse_duration_to_seconds(self, duration_str: str) -> int:
        """Convert duration string like '35:49' or '1:02:08' to seconds"""
        if not duration_str:
            return 0
        
        try:
            parts = duration_str.split(':')
            if len(parts) == 2:  # MM:SS
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
            elif len(parts) == 3:  # HH:MM:SS
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
        except Exception:
            pass
        
        return 0

    def parse_pace_to_seconds(self, pace_str: str) -> Optional[int]:
        """Convert pace string like '10:49/mi' to seconds per mile"""
        if not pace_str or '/mi' not in pace_str:
            return None
        
        try:
            pace_part = pace_str.replace('/mi', '').strip()
            parts = pace_part.split(':')
            if len(parts) == 2:
                minutes, seconds = map(int, parts)
                return minutes * 60 + seconds
        except Exception:
            pass
        
        return None

    def convert_laps_to_splits(self, laps: List[Dict]) -> List[Dict]:
        """Convert lap data to splits format with enhanced per-split running dynamics"""
        splits = []
        
        for i, lap in enumerate(laps):
            # Parse lap data
            distance_str = lap.get('distance', '')
            distance_mi = 0
            if 'mi' in distance_str:
                distance_mi = float(distance_str.replace('mi', '').strip())
            
            time_str = lap.get('time', '')
            mile_time_s = self.parse_duration_to_seconds(time_str)
            
            pace_str = lap.get('pace', '')
            avg_pace_s_per_mi = self.parse_pace_to_seconds(pace_str)
            
            elevation_str = lap.get('elevation', '')
            elev_gain_ft = 0
            if 'ft' in elevation_str:
                elev_gain_ft = int(elevation_str.replace('ft', '').strip())
            
            hr_str = lap.get('heartRate', '')
            avg_hr = None
            if 'bpm' in hr_str:
                avg_hr = int(hr_str.replace('bpm', '').strip())
            
            split = {
                "split": i + 1,  # CHANGED from "mile" to "split"
                "avg_hr": avg_hr,
                "max_hr": avg_hr,  # Will be enhanced from FIT data if available
                "avg_pace_s_per_mi": avg_pace_s_per_mi,
                "mile_time_s": mile_time_s,
                "elev_gain_ft": elev_gain_ft,
                "step_type": lap.get('stepType')  # From FIT data if available
            }
            
            # Add per-split running dynamics if available (from FIT file)
            if lap.get('runningDynamics'):
                split["running_dynamics"] = lap['runningDynamics']
            
            splits.append(split)
        
        return splits

    def generate_daily_file_content(self, daily_data: Dict) -> str:
        """Generate complete daily file content with multipage design"""
        
        # Generate YAML front matter
        yaml_content = yaml.dump(daily_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        # Generate human-readable summary
        summary_content = self.generate_summary_section(daily_data)
        
        # Generate structured readable sections
        structured_content = self.generate_structured_readable_sections(daily_data)
        
        # Generate expandable JSON section
        json_content = json.dumps(daily_data, indent=2)
        
        # Combine all sections
        full_content = f"""---
{yaml_content}---
{summary_content}

{structured_content}

<details>
<summary>Full JSON</summary>

```json
{json_content}
```
</details>
"""
        
        return full_content

    def generate_summary_section(self, daily_data: Dict) -> str:
        """Generate the daily summary section (REMOVED redundant totals)"""
        date = daily_data.get('date', '')
        
        # NO MORE TOTALS/SLEEP SUMMARY - just the title
        return f"# {date} · Daily Summary"

    def get_smart_metric_layout(self, metrics: List[Dict]) -> str:
        """Generate smart metric layout that avoids awkward two-line displays"""
        if not metrics:
            return ""
        
        # Calculate if metrics will be too cramped in 2-column grid
        long_metrics = []
        short_metrics = []
        
        for metric in metrics:
            label_length = len(metric['label'])
            value_length = len(str(metric['value']))
            total_length = label_length + value_length
            
            # If combined length > 12 characters, treat as long
            if total_length > 12:
                long_metrics.append(metric)
            else:
                short_metrics.append(metric)
        
        html = ""
        
        # If we have any long metrics, use single column for all to maintain consistency
        if long_metrics:
            html += '<div class="metric-list">'
            for metric in metrics:
                html += f'<div class="metric-item-full"><span class="metric-label">{metric["label"]}</span><span class="metric-value">{metric["value"]}</span></div>'
            html += '</div>'
        else:
            # All metrics are short, safe to use 2-column grid
            html += '<div class="metric-grid">'
            for metric in metrics:
                html += f'<div class="metric-item"><span class="metric-label">{metric["label"]}</span><span class="metric-value">{metric["value"]}</span></div>'
            html += '</div>'
        
        return html

    def generate_html_table(self, splits: List[Dict]) -> str:
        """Generate proper HTML table for splits"""
        if not splits:
            return ""
        
        html = '<table class="splits-table">'
        
        # Table header
        html += '<thead><tr>'
        html += '<th>Split</th><th>Time</th><th>Pace</th><th>HR Avg</th><th>HR Max</th>'
        html += '<th>Elev</th><th>Cadence</th><th>Stride</th><th>GCT</th><th>VO</th>'
        html += '</tr></thead>'
        
        # Table body
        html += '<tbody>'
        for split in splits:
            html += '<tr>'
            
            # Split number
            split_num = split.get('split', split.get('mile', '?'))
            html += f'<td>{split_num}</td>'
            
            # Time
            time_s = split.get('mile_time_s', 0)
            time_str = self.format_time_duration(time_s) if time_s > 0 else "N/A"
            html += f'<td>{time_str}</td>'
            
            # Pace
            pace_str = self.format_pace(split.get('avg_pace_s_per_mi')) if split.get('avg_pace_s_per_mi') else "N/A"
            html += f'<td>{pace_str}</td>'
            
            # Heart rate
            hr_avg = split.get('avg_hr', '') or 'N/A'
            hr_max = split.get('max_hr', '') or 'N/A'
            html += f'<td>{hr_avg}</td><td>{hr_max}</td>'
            
            # Elevation
            elev = split.get('elev_gain_ft', 0)
            elev_str = f"{elev:+d} ft" if elev != 0 else "0 ft"
            html += f'<td>{elev_str}</td>'
            
            # Running dynamics (per-split)
            cadence = stride = gct = vo = "N/A"
            if split.get('running_dynamics'):
                rd = split['running_dynamics']
                if rd.get('cadence_spm'):
                    cadence = f"{rd['cadence_spm']} spm"
                if rd.get('stride_length_cm'):
                    stride = f"{rd['stride_length_cm']} cm"
                if rd.get('ground_contact_time_ms'):
                    gct = f"{rd['ground_contact_time_ms']} ms"
                if rd.get('vertical_oscillation_mm'):
                    vo = f"{rd['vertical_oscillation_mm']} mm"
            
            html += f'<td>{cadence}</td><td>{stride}</td><td>{gct}</td><td>{vo}</td>'
            html += '</tr>'
        
        html += '</tbody></table>'
        return html

    def generate_mobile_cards_html(self, splits: List[Dict]) -> str:
        """Generate mobile-friendly cards for splits data"""
        if not splits:
            return ""
        
        html = '<div class="mobile-splits">'
        
        for i, split in enumerate(splits, 1):
            html += f'<div class="mobile-split-card">'
            html += f'<div class="mobile-split-header">Split {i}</div>'
            
            # Time
            time_s = split.get('mile_time_s', 0)
            if time_s > 0:
                if time_s >= 60:
                    minutes = time_s // 60
                    seconds = time_s % 60
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{time_s}s"
            else:
                time_str = "N/A"
            html += f'<div class="mobile-split-row"><span class="mobile-split-label">Time</span><span class="mobile-split-value">{time_str}</span></div>'
            
            # Pace
            if split.get('avg_pace_s_per_mi'):
                pace_s = split['avg_pace_s_per_mi']
                pace_min = pace_s // 60
                pace_sec = pace_s % 60
                pace_str = f"{pace_min}:{pace_sec:02d}/mi"
            else:
                pace_str = "N/A"
            html += f'<div class="mobile-split-row"><span class="mobile-split-label">Pace</span><span class="mobile-split-value">{pace_str}</span></div>'
            
            # Heart Rate
            hr_avg = split.get('avg_hr', '') or 'N/A'
            hr_max = split.get('max_hr', '') or 'N/A'
            html += f'<div class="mobile-split-row"><span class="mobile-split-label">HR Avg</span><span class="mobile-split-value">{hr_avg}</span></div>'
            html += f'<div class="mobile-split-row"><span class="mobile-split-label">HR Max</span><span class="mobile-split-value">{hr_max}</span></div>'
            
            # Elevation
            elev = split.get('elev_gain_ft', 0)
            elev_str = f"{elev:+d} ft" if elev != 0 else "0 ft"
            html += f'<div class="mobile-split-row"><span class="mobile-split-label">Elevation</span><span class="mobile-split-value">{elev_str}</span></div>'
            
            # Running dynamics if available
            if split.get('running_dynamics'):
                rd = split['running_dynamics']
                if rd.get('cadence_spm'):
                    html += f'<div class="mobile-split-row"><span class="mobile-split-label">Cadence</span><span class="mobile-split-value">{rd["cadence_spm"]:.0f} spm</span></div>'
                if rd.get('stride_length_cm'):
                    html += f'<div class="mobile-split-row"><span class="mobile-split-label">Stride</span><span class="mobile-split-value">{rd["stride_length_cm"]:.0f} cm</span></div>'
            
            html += '</div>'  # Close card
        
        html += '</div>'  # Close mobile-splits
        return html

    def get_navigation_buttons(self, current_date: str) -> str:
        """Generate navigation buttons with PROPER paths (fixes 404 issue)"""
        try:
            from datetime import datetime, timedelta
            dt = datetime.strptime(current_date, '%Y-%m-%d')
            prev_date = dt - timedelta(days=1)
            next_date = dt + timedelta(days=1)
            
            # Use proper relative paths WITHOUT .md extension
            prev_path = f"../07/{prev_date.day:02d}" if prev_date.month == 7 else f"../{prev_date.month:02d}/{prev_date.day:02d}"
            next_path = f"{next_date.day:02d}" if next_date.month == dt.month else f"../{next_date.month:02d}/{next_date.day:02d}"
            
            # Check if files exist
            from pathlib import Path
            prev_file_path = Path(f"data/{prev_date.year}/{prev_date.month:02d}/{prev_date.day:02d}.md")
            next_file_path = Path(f"data/{next_date.year}/{next_date.month:02d}/{next_date.day:02d}.md")
            
            prev_exists = prev_file_path.exists()
            next_exists = next_file_path.exists()
            
            nav_html = '<div class="navigation-bar">'
            
            if prev_exists:
                nav_html += f'<a href="{prev_path}" class="nav-button nav-prev">← {prev_date.strftime("%b %d")}</a>'
            else:
                nav_html += '<span class="nav-disabled">← Previous</span>'
            
            nav_html += f'<span class="nav-current">{dt.strftime("%B %d, %Y")}</span>'
            
            if next_exists:
                nav_html += f'<a href="{next_path}" class="nav-button nav-next">{next_date.strftime("%b %d")} →</a>'
            else:
                nav_html += '<span class="nav-disabled">Next →</span>'
            
            nav_html += '</div>'
            return nav_html
            
        except Exception as e:
            logger.warning(f"Could not generate navigation for date {current_date}: {e}")
            return ""

    def get_comprehensive_css(self) -> str:
        """Generate refined CSS with all fixes"""
        return """<style>
/* Global Styles */
body { 
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    line-height: 1.6;
    color: #2d3748;
    background-color: #f7fafc;
    margin: 0;
    padding: 20px;
}

/* Navigation Bar */
.navigation-bar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin: 0 0 32px 0;
    padding: 16px 24px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.nav-button {
    display: inline-block;
    padding: 10px 20px;
    background-color: rgba(255,255,255,0.2);
    color: white;
    text-decoration: none;
    border-radius: 8px;
    font-weight: 600;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);
}

.nav-button:hover {
    background-color: rgba(255,255,255,0.3);
    transform: translateY(-2px);
    box-shadow: 0 4px 8px rgba(0,0,0,0.2);
}

.nav-current {
    font-weight: 700;
    font-size: 1.1em;
    color: white;
    text-shadow: 0 2px 4px rgba(0,0,0,0.3);
}

.nav-disabled {
    color: rgba(255,255,255,0.5);
    font-weight: 500;
}

/* Page Title */
h1 {
    font-size: 2.5em;
    font-weight: 800;
    color: #2d3748;
    margin: 0 0 32px 0;
    text-align: center;
    background: linear-gradient(135deg, #667eea, #764ba2);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}

/* Card Container */
.card-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 24px;
    margin-bottom: 32px;
}

/* Base Card Styles - DARKER BACKGROUNDS */
.metric-card {
    background: linear-gradient(145deg, #f1f5f9, #e2e8f0); /* DARKER */
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.12);
    border-left: 5px solid #e2e8f0;
    transition: all 0.3s ease;
    position: relative;
    overflow: hidden;
}

.metric-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px rgba(0,0,0,0.15);
}

/* Card Type Specific Styling - DARKER BACKGROUNDS */
.sleep-card { 
    border-left-color: #3b82f6;
    background: linear-gradient(145deg, #e0f2fe, #b3e5fc); /* DARKER */
}

.wellness-card { 
    border-left-color: #10b981;
    background: linear-gradient(145deg, #dcfce7, #bbf7d0); /* DARKER */
}

.workout-card { 
    border-left-color: #f59e0b;
    background: linear-gradient(145deg, #fef3c7, #fde68a); /* DARKER */
}

/* Card Headers */
.card-header {
    font-size: 1.3em;
    font-weight: 700;
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 8px;
    color: #1f2937;
}

.card-emoji {
    font-size: 1.5em;
}

/* SMART METRIC LAYOUTS */
/* Two-column grid for short metrics */
.metric-grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin: 16px 0;
}

/* Single column list for long metrics to avoid awkward wrapping */
.metric-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin: 16px 0;
}

/* Standard metric items (2-column grid) */
.metric-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 18px;
    background: rgba(255,255,255,0.9);
    border-radius: 10px;
    transition: all 0.2s ease;
    border: 1px solid rgba(255,255,255,0.8);
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

/* Full-width metric items (single column) for longer content */
.metric-item-full {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 14px 18px;
    background: rgba(255,255,255,0.9);
    border-radius: 10px;
    transition: all 0.2s ease;
    border: 1px solid rgba(255,255,255,0.8);
    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    width: 100%;
}

.metric-item:hover, .metric-item-full:hover {
    background: rgba(255,255,255,0.95);
    transform: translateY(-1px);
}

/* IMPROVED LABEL/VALUE DISTINCTION */
.metric-label {
    font-weight: 600;
    color: #6b7280;
    font-size: 0.85em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    flex-shrink: 0;
}

.metric-value {
    font-weight: 800;
    color: #1f2937;
    font-size: 1.1em;
    margin-left: 12px;
    text-align: right;
}

.metric-primary {
    font-size: 1.6em;
    font-weight: 900; /* EXTRA BOLD */
    color: #1f2937;
    text-align: center;
    margin: 12px 0;
    padding: 20px;
    background: rgba(255,255,255,0.95); /* DARKER BACKGROUND */
    border-radius: 12px;
    border: 2px solid rgba(255,255,255,0.9);
    box-shadow: 0 3px 8px rgba(0,0,0,0.08);
}

/* Workout Detail Card - DARKER BACKGROUND */
.workout-detail-card {
    grid-column: 1 / -1;
    background: linear-gradient(145deg, #f1f5f9, #e2e8f0); /* DARKER */
    border-radius: 16px;
    padding: 32px;
    box-shadow: 0 6px 25px rgba(0,0,0,0.12);
    border-left: 5px solid #f59e0b;
    margin: 24px 0;
}

.workout-sections {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 24px;
    margin: 24px 0;
}

.workout-section {
    background: rgba(255,255,255,0.9); /* DARKER BACKGROUND */
    border-radius: 12px;
    padding: 20px;
    border: 1px solid rgba(229,231,235,0.9);
    box-shadow: 0 2px 6px rgba(0,0,0,0.05);
}

.section-title {
    font-weight: 700;
    font-size: 1.1em;
    color: #374151;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid #e5e7eb;
}

/* ENHANCED TABLE STYLING TO MATCH CARD DESIGN */
.splits-section {
    margin: 32px 0;
    grid-column: 1 / -1;
}

.splits-section h2 {
    color: #1f2937;
    font-weight: 700;
    margin-bottom: 24px;
    font-size: 1.4em;
    display: flex;
    align-items: center;
    gap: 8px;
}

/* CARD-STYLE TABLE CONTAINER */
.table-container {
    background: linear-gradient(145deg, #f1f5f9, #e2e8f0);
    border-radius: 16px;
    padding: 24px;
    box-shadow: 0 6px 25px rgba(0,0,0,0.12);
    border-left: 5px solid #10b981;
    margin: 20px 0;
    overflow: hidden;
}

/* IMPROVED HTML TABLE STYLES */
.splits-table {
    border-collapse: collapse;
    width: 100%;
    margin: 0;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 4px 15px rgba(0,0,0,0.08);
    background: white;
    font-family: inherit;
}

.splits-table th {
    background: linear-gradient(135deg, #1f2937, #374151);
    color: white;
    padding: 16px 12px;
    text-align: center;
    font-weight: 700;
    font-size: 0.85em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: none;
    position: relative;
}

.splits-table th:first-child {
    border-top-left-radius: 12px;
}

.splits-table th:last-child {
    border-top-right-radius: 12px;
}

.splits-table td {
    padding: 14px 10px;
    text-align: center;
    border: 1px solid #e5e7eb;
    font-weight: 500;
    font-size: 0.9em;
    transition: all 0.2s ease;
}

/* ENHANCED alternating rows with better contrast */
.splits-table tr:nth-child(even) {
    background: linear-gradient(145deg, #f8fafc, #f1f5f9);
}

.splits-table tr:nth-child(odd) {
    background: #ffffff;
}

.splits-table tbody tr:hover {
    background: linear-gradient(135deg, #dbeafe, #bfdbfe) !important;
    transform: scale(1.01);
    box-shadow: 0 2px 8px rgba(59, 130, 246, 0.15);
    transition: all 0.2s ease;
}

/* MOBILE-RESPONSIVE TABLE DESIGN */
@media (max-width: 768px) {
    /* Hide the table and show mobile cards instead */
    .splits-table {
        display: none;
    }
    
    /* Mobile card-based layout */
    .mobile-splits {
        display: block;
    }
    
    .mobile-split-card {
        background: rgba(255,255,255,0.95);
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 16px;
        border: 1px solid rgba(229,231,235,0.9);
        box-shadow: 0 2px 6px rgba(0,0,0,0.05);
        transition: all 0.2s ease;
    }
    
    .mobile-split-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
    }
    
    .mobile-split-header {
        font-weight: 700;
        font-size: 1.1em;
        color: #1f2937;
        margin-bottom: 12px;
        padding-bottom: 8px;
        border-bottom: 2px solid #e5e7eb;
        text-align: center;
    }
    
    .mobile-split-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 6px 0;
        border-bottom: 1px solid #f3f4f6;
    }
    
    .mobile-split-row:last-child {
        border-bottom: none;
    }
    
    .mobile-split-label {
        font-weight: 600;
        color: #6b7280;
        font-size: 0.85em;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    
    .mobile-split-value {
        font-weight: 700;
        color: #1f2937;
        font-size: 0.95em;
    }
    
    /* Smaller table container padding on mobile */
    .table-container {
        padding: 16px;
        margin: 16px 0;
    }
}

/* DESKTOP: Hide mobile cards */
@media (min-width: 769px) {
    .mobile-splits {
        display: none;
    }
}

/* EXTRA WIDE SCREENS: Better table spacing */
@media (min-width: 1200px) {
    .splits-table th,
    .splits-table td {
        padding: 16px 14px;
    }
    
    .table-container {
        padding: 32px;
    }
}

/* PROGRESSIVE DISCLOSURE - IMPROVED STYLING */
.collapsible {
    cursor: pointer;
    padding: 16px 20px;
    background: linear-gradient(135deg, #e5e7eb, #d1d5db);
    border: none;
    border-radius: 10px;
    text-align: left;
    outline: none;
    font-size: 1em;
    font-weight: 600;
    margin: 12px 0;
    transition: all 0.3s ease;
    width: 100%;
    color: #374151;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.collapsible:hover {
    background: linear-gradient(135deg, #d1d5db, #9ca3af);
    color: white;
}

.collapsible:after {
    content: '\\002B';
    color: #6b7280;
    font-weight: bold;
    float: right;
    margin-left: 5px;
}

.active:after {
    content: "\\2212";
}

.collapsible-content {
    padding: 0 20px;
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.3s ease-out;
    background: rgba(255,255,255,0.9);
    border-radius: 0 0 8px 8px;
}

/* EXPANDED COLLAPSIBLE CONTENT STYLING */
.collapsible-content p {
    margin: 12px 0;
    padding: 8px 12px;
    background: rgba(255,255,255,0.8);
    border-radius: 6px;
    border-left: 3px solid #e5e7eb;
}

/* COLOR-CODED HR ZONES */
.zone-distribution {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    margin: 12px 0;
}

.zone-item {
    padding: 8px 14px;
    border-radius: 20px;
    font-size: 0.85em;
    font-weight: 600;
    border: 2px solid;
    color: white;
    text-shadow: 0 1px 2px rgba(0,0,0,0.3);
}

/* COLOR-CODED BY ZONE */
.zone-item.zone-1 {
    background: linear-gradient(135deg, #6b7280, #9ca3af);
    border-color: #4b5563;
}

.zone-item.zone-2 {
    background: linear-gradient(135deg, #3b82f6, #60a5fa);
    border-color: #2563eb;
}

.zone-item.zone-3 {
    background: linear-gradient(135deg, #10b981, #34d399);
    border-color: #059669;
}

.zone-item.zone-4 {
    background: linear-gradient(135deg, #f59e0b, #fbbf24);
    border-color: #d97706;
}

.zone-item.zone-5 {
    background: linear-gradient(135deg, #ef4444, #f87171);
    border-color: #dc2626;
}

/* Responsive Design */
@media (max-width: 768px) {
    .card-container {
        grid-template-columns: 1fr;
    }
    
    .workout-sections {
        grid-template-columns: 1fr;
    }
    
    .metric-grid {
        grid-template-columns: 1fr;
    }
    
    .navigation-bar {
        flex-direction: column;
        gap: 12px;
        text-align: center;
    }
    
    h1 {
        font-size: 2em;
    }
    
    .splits-table {
        font-size: 0.8em;
    }
    
    .splits-table th, .splits-table td {
        padding: 8px 6px;
    }
}
</style>"""

    def generate_structured_readable_sections(self, daily_data: Dict) -> str:
        """Generate beautiful card-based layout sections"""
        content = []
        date = daily_data.get('date', '')
        
        # Add comprehensive CSS
        content.append(self.get_comprehensive_css())
        content.append("")
        
        # Add navigation buttons with proper paths
        nav_buttons = self.get_navigation_buttons(date)
        if nav_buttons:
            content.append(nav_buttons)
            content.append("")
        
        # Three-column card container
        content.append('<div class="card-container">')
        
        # Sleep Health Card
        content.append('<div class="metric-card sleep-card">')
        content.append('<div class="card-header"><span class="card-emoji">🛌</span>Sleep Health</div>')
        
        sleep = daily_data.get('sleep_metrics', {})
        if any(v is not None for v in sleep.values()):
            if sleep.get('sleep_minutes'):
                hours = sleep['sleep_minutes'] // 60
                mins = sleep['sleep_minutes'] % 60
                content.append(f'<div class="metric-primary">{hours}h {mins}m total</div>')
            
            # Use smart metric layout for sleep (these are short, use grid)
            content.append('<div class="metric-grid">')
            if sleep.get('sleep_score'):
                content.append(f'<div class="metric-item"><span class="metric-label">Score</span><span class="metric-value">{sleep["sleep_score"]}</span></div>')
            if sleep.get('hrv_night_avg'):
                content.append(f'<div class="metric-item"><span class="metric-label">HRV</span><span class="metric-value">{sleep["hrv_night_avg"]}ms</span></div>')
            content.append('</div>')
            
            # IMPROVED Sleep breakdown - All stages included and properly formatted
            content.append('<button class="collapsible">Sleep Breakdown</button>')
            content.append('<div class="collapsible-content">')
            if sleep.get('deep_minutes'):
                content.append(f'<p><strong>Deep Sleep:</strong> {sleep["deep_minutes"]}m</p>')
            if sleep.get('light_minutes'):
                content.append(f'<p><strong>Light Sleep:</strong> {sleep["light_minutes"]}m</p>')
            if sleep.get('rem_minutes'):
                content.append(f'<p><strong>REM Sleep:</strong> {sleep["rem_minutes"]}m</p>')
            if sleep.get('awake_minutes'):
                content.append(f'<p><strong>Awake Time:</strong> {sleep["awake_minutes"]}m</p>')
            content.append('</div>')
        else:
            content.append('<div class="metric-primary">No sleep data</div>')
        
        content.append('</div>')  # End sleep card

        # Daily Wellness Card
        content.append('<div class="metric-card wellness-card">')
        content.append('<div class="card-header"><span class="card-emoji">⚡</span>Daily Wellness</div>')
        
        daily = daily_data.get('daily_metrics', {})
        if daily.get('steps'):
            content.append(f'<div class="metric-primary">{daily["steps"]:,} steps</div>')
        
        # Prepare metrics for smart layout
        wellness_metrics = []
        bb = daily.get('body_battery', {})
        if bb.get('charge') is not None and bb.get('charge') > 0:
            wellness_metrics.append({"label": "Battery", "value": f"+{bb['charge']}"})
        elif bb.get('drain') is not None and bb.get('drain') > 0:
            wellness_metrics.append({"label": "Battery", "value": f"-{bb['drain']}"})
        
        if daily.get('resting_hr'):
            wellness_metrics.append({"label": "RHR", "value": f"{daily['resting_hr']} bpm"})
        
        if daily.get('lactate_threshold'):
            lt = daily['lactate_threshold']
            if lt.get('heart_rate_bpm'):
                wellness_metrics.append({"label": "LT", "value": f"{lt['heart_rate_bpm']} bpm"})
        
        content.append(self.get_smart_metric_layout(wellness_metrics))
        
        content.append('</div>')  # End wellness card

        # Workout Stats Card
        workouts = daily_data.get('workout_metrics', [])
        if workouts:
            workout = workouts[0]  # Primary workout
            content.append('<div class="metric-card workout-card">')
            content.append(f'<div class="card-header"><span class="card-emoji">🏃</span>{workout.get("type", "Workout")} Stats</div>')
            
            if workout.get('distance_mi'):
                content.append(f'<div class="metric-primary">{workout["distance_mi"]:.2f} mi</div>')
            
            # Prepare metrics for smart layout
            workout_metrics = []
            if workout.get('moving_time_s'):
                time_str = self.format_time_duration(workout['moving_time_s'])
                workout_metrics.append({"label": "Time", "value": time_str})
            if workout.get('avg_pace_s_per_mi'):
                pace_str = self.format_pace(workout['avg_pace_s_per_mi'])
                workout_metrics.append({"label": "Pace", "value": pace_str})
            if workout.get('avg_hr'):
                workout_metrics.append({"label": "Avg HR", "value": f"{workout['avg_hr']} bpm"})
            if workout.get('training_effects', {}).get('label'):
                label = workout['training_effects']['label']
                workout_metrics.append({"label": "Type", "value": label})
            
            content.append(self.get_smart_metric_layout(workout_metrics))
            content.append('</div>')  # End workout card
        
        content.append('</div>')  # End card container

        # Detailed Workout Card (Full Width)
        if workouts:
            content.append('<div class="workout-detail-card">')
            content.append(f'<div class="card-header"><span class="card-emoji">🏃‍♂️</span>{workout.get("type", "Workout")} Details - {workout.get("location", "Unknown Location")}</div>')
            
            content.append('<div class="workout-sections">')
            
            # Course Section
            content.append('<div class="workout-section">')
            content.append('<div class="section-title">📍 Course</div>')
            if workout.get('distance_mi'):
                content.append(f'<p><strong>Distance:</strong> {workout["distance_mi"]:.2f} mi</p>')
            if workout.get('elev_gain_ft'):
                content.append(f'<p><strong>Elevation:</strong> {workout["elev_gain_ft"]} ft gain</p>')
            if workout.get('moving_time_s'):
                time_str = self.format_time_duration(workout['moving_time_s'])
                content.append(f'<p><strong>Duration:</strong> {time_str}</p>')
            content.append('</div>')
            
            # Conditions Section
            if workout.get('weather'):
                content.append('<div class="workout-section">')
                content.append('<div class="section-title">🌤️ Conditions</div>')
                weather = workout['weather']
                if weather.get('temperature'):
                    temp = weather['temperature']
                    content.append(f'<p><strong>Temperature:</strong> {temp.get("start", "?")}°F → {temp.get("end", "?")}°F</p>')
                if weather.get('conditions'):
                    content.append(f'<p><strong>Weather:</strong> {weather["conditions"]}</p>')
                if weather.get('humidity'):
                    humidity = weather['humidity']
                    content.append(f'<p><strong>Humidity:</strong> {humidity.get("start", "?")}% → {humidity.get("end", "?")}%</p>')
                content.append('</div>')
            
            # Performance Section
            content.append('<div class="workout-section">')
            content.append('<div class="section-title">❤️ Performance</div>')
            if workout.get('avg_hr') and workout.get('max_hr'):
                content.append(f'<p><strong>Heart Rate:</strong> {workout["avg_hr"]} avg, {workout["max_hr"]} max</p>')
            if workout.get('avg_pace_s_per_mi'):
                pace_str = self.format_pace(workout['avg_pace_s_per_mi'])
                content.append(f'<p><strong>Average Pace:</strong> {pace_str}</p>')
            
            # COLOR-CODED HR ZONES
            if workout.get('hr_zones'):
                zone_html = '<div class="zone-distribution">'
                for zone, time in workout['hr_zones'].items():
                    if time != "0:00":
                        zone_num = zone.replace('zone_', '')
                        zone_html += f'<span class="zone-item zone-{zone_num}">Z{zone_num.upper()}: {time}</span>'
                zone_html += '</div>'
                content.append(f'<p><strong>HR Zones:</strong></p>{zone_html}')
            content.append('</div>')
            
            content.append('</div>')  # End workout sections
            
            # Training Load Collapsible
            if workout.get('training_effects'):
                content.append('<button class="collapsible">Training Effects & Load</button>')
                content.append('<div class="collapsible-content">')
                effects = workout['training_effects']
                if effects.get('aerobic'):
                    content.append(f'<p><strong>Aerobic Effect:</strong> {effects["aerobic"]}</p>')
                if effects.get('anaerobic'):
                    content.append(f'<p><strong>Anaerobic Effect:</strong> {effects["anaerobic"]}</p>')
                if effects.get('training_load'):
                    content.append(f'<p><strong>Training Load:</strong> {effects["training_load"]}</p>')
                content.append('</div>')
            
            # Running Form Collapsible
            if workout.get('running_dynamics'):
                content.append('<button class="collapsible">Running Form Analysis</button>')
                content.append('<div class="collapsible-content">')
                dynamics = workout['running_dynamics']
                if dynamics.get('cadence_spm'):
                    content.append(f'<p><strong>Cadence:</strong> {dynamics["cadence_spm"]} spm</p>')
                if dynamics.get('stride_length_cm'):
                    content.append(f'<p><strong>Stride Length:</strong> {dynamics["stride_length_cm"]} cm</p>')
                if dynamics.get('ground_contact_time_ms'):
                    content.append(f'<p><strong>Ground Contact:</strong> {dynamics["ground_contact_time_ms"]} ms</p>')
                if dynamics.get('vertical_oscillation_mm'):
                    content.append(f'<p><strong>Vertical Oscillation:</strong> {dynamics["vertical_oscillation_mm"]} mm</p>')
                content.append('</div>')
            
            # Power Data Collapsible
            if workout.get('power'):
                content.append('<button class="collapsible">Power Analysis</button>')
                content.append('<div class="collapsible-content">')
                power = workout['power']
                if power.get('average'):
                    content.append(f'<p><strong>Average Power:</strong> {power["average"]}W</p>')
                if power.get('normalized'):
                    content.append(f'<p><strong>Normalized Power:</strong> {power["normalized"]}W</p>')
                if power.get('maximum'):
                    content.append(f'<p><strong>Maximum Power:</strong> {power["maximum"]}W</p>')
                content.append('</div>')
            
            content.append('</div>')  # End workout detail card

            # IMPROVED HTML TABLE for Splits with Card Styling
            splits = workout.get('splits', [])
            if splits:
                content.append('<div class="splits-section">')
                content.append('<h2>📊 Split Analysis</h2>')
                content.append('<div class="table-container">')
                content.append(self.generate_html_table(splits))
                content.append(self.generate_mobile_cards_html(splits))
                content.append('</div>')
                content.append('</div>')  # End splits section

        # JavaScript for collapsible functionality
        content.append("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    var coll = document.getElementsByClassName("collapsible");
    var i;

    for (i = 0; i < coll.length; i++) {
        coll[i].addEventListener("click", function() {
            this.classList.toggle("active");
            var content = this.nextElementSibling;
            if (content.style.maxHeight){
                content.style.maxHeight = null;
            } else {
                content.style.maxHeight = content.scrollHeight + "px";
            } 
        });
    }
});
</script>""")
        
        return '\n'.join(content)

    def format_time_duration(self, seconds: int) -> str:
        """Format seconds to human readable duration"""
        if seconds <= 0:
            return "0s"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours} h {minutes} m"
        elif minutes > 0:
            return f"{minutes} m {secs} s"
        else:
            return f"{secs}s"

    def format_pace(self, seconds_per_mile: int) -> str:
        """Format pace in seconds per mile to MM:SS/mi"""
        if not seconds_per_mile or seconds_per_mile <= 0:
            return "N/A"
        
        minutes = seconds_per_mile // 60
        seconds = seconds_per_mile % 60
        return f"{minutes}:{seconds:02d}/mi"

    def write_daily_file(self, date_str: str, daily_data: Dict):
        """Write daily data to file"""
        # Parse date to create directory structure
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        year_dir = self.data_dir / str(dt.year)
        month_dir = year_dir / f"{dt.month:02d}"
        
        # Create directories
        month_dir.mkdir(parents=True, exist_ok=True)
        
        # Write file
        file_path = month_dir / f"{dt.day:02d}.md"
        content = self.generate_daily_file_content(daily_data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Created daily file: {file_path}")

    def update_last_id(self, activities: List[Dict]):
        """Update last_id.json with the newest activity"""
        if not activities:
            return
        
        # Find the newest activity by ID
        newest_activity = max(activities, key=lambda x: int(x.get('activityId', '0')))
        
        last_data = {
            "last_id": newest_activity.get('activityId'),
            "last_date": self.extract_date_from_activity(newest_activity)
        }
        
        with open(self.last_id_file, 'w') as f:
            json.dump(last_data, f, indent=2)
        
        logger.info(f"Updated last_id.json to: ID={last_data['last_id']}, Date={last_data['last_date']}")

    def process_activities(self):
        """Main processing function"""
        logger.info("Starting Garmin to daily files conversion...")
        
        # Read activities from scraper output
        try:
            with open(self.activities_path, 'r') as f:
                activities = json.load(f)
        except FileNotFoundError:
            logger.error("activities.json not found. Run the Garmin scraper first.")
            return
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in activities.json: {e}")
            return
        
        if not activities:
            logger.info("No activities to process.")
            return
        
        logger.info(f"Processing {len(activities)} activities")
        
        # Convert to daily data structure
        daily_data = self.convert_old_activities_to_new_format(activities)
        
        # Write daily files
        for date_str, data in daily_data.items():
            self.write_daily_file(date_str, data)
        
        # Update last_id tracking
        self.update_last_id(activities)
        
        logger.info(f"Successfully created {len(daily_data)} daily files")

def main():
    """Main entry point"""
    try:
        converter = GarminToDailyFiles()
        converter.process_activities()
    except Exception as e:
        logger.error(f"Conversion failed: {e}")
        exit(1)

if __name__ == "__main__":
    main() 