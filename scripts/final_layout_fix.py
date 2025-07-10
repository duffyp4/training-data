#!/usr/bin/env python3
"""
Final Layout Fix Script
Fixes:
1. Awkward two-line metrics with better layout decisions
2. Convert table to proper HTML format for guaranteed rendering
3. Smart metric display based on content length
"""

import json
import os
import yaml
import re
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Dict, Optional, List
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class FinalLayoutFixer:
    def __init__(self):
        pass

    def parse_yaml_frontmatter(self, file_path: Path) -> Optional[Dict]:
        """Parse YAML frontmatter from a markdown file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    yaml_content = parts[1]
                    return yaml.safe_load(yaml_content)
        except Exception as e:
            logger.error(f"Error parsing YAML from {file_path}: {e}")
        return None

    def format_time_duration(self, seconds: int) -> str:
        """Format seconds to human readable duration"""
        if seconds <= 0:
            return "0s"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        elif minutes > 0:
            return f"{minutes}m {secs}s"
        else:
            return f"{secs}s"

    def format_pace(self, seconds_per_mile: int) -> str:
        """Format pace in seconds per mile to MM:SS/mi"""
        if not seconds_per_mile or seconds_per_mile <= 0:
            return "N/A"
        
        minutes = seconds_per_mile // 60
        seconds = seconds_per_mile % 60
        return f"{minutes}:{seconds:02d}/mi"

    def get_navigation_buttons(self, current_date: str) -> str:
        """Generate navigation buttons with proper paths"""
        try:
            dt = datetime.strptime(current_date, '%Y-%m-%d')
            prev_date = dt - timedelta(days=1)
            next_date = dt + timedelta(days=1)
            
            # Use proper relative paths WITHOUT .md extension
            prev_path = f"../07/{prev_date.day:02d}" if prev_date.month == 7 else f"../{prev_date.month:02d}/{prev_date.day:02d}"
            next_path = f"{next_date.day:02d}" if next_date.month == dt.month else f"../{next_date.month:02d}/{next_date.day:02d}"
            
            # Check if files exist
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

    def get_comprehensive_css(self) -> str:
        """Generate refined CSS with smart metric layouts and HTML table support"""
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
    background: linear-gradient(145deg, #f1f5f9, #e2e8f0);
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
    background: linear-gradient(145deg, #e0f2fe, #b3e5fc);
}

.wellness-card { 
    border-left-color: #10b981;
    background: linear-gradient(145deg, #dcfce7, #bbf7d0);
}

.workout-card { 
    border-left-color: #f59e0b;
    background: linear-gradient(145deg, #fef3c7, #fde68a);
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
    font-weight: 900;
    color: #1f2937;
    text-align: center;
    margin: 12px 0;
    padding: 20px;
    background: rgba(255,255,255,0.95);
    border-radius: 12px;
    border: 2px solid rgba(255,255,255,0.9);
    box-shadow: 0 3px 8px rgba(0,0,0,0.08);
}

/* Workout Detail Card - DARKER BACKGROUND */
.workout-detail-card {
    grid-column: 1 / -1;
    background: linear-gradient(145deg, #f1f5f9, #e2e8f0);
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
    background: rgba(255,255,255,0.9);
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

/* PROPER HTML TABLE STYLING */
.splits-section {
    margin: 32px 0;
    grid-column: 1 / -1;
}

.splits-section h2 {
    color: #1f2937;
    font-weight: 700;
    margin-bottom: 20px;
    font-size: 1.4em;
}

/* HTML Table Styles */
.splits-table {
    border-collapse: collapse;
    width: 100%;
    margin: 20px 0;
    border-radius: 12px;
    overflow: hidden;
    box-shadow: 0 6px 25px rgba(0,0,0,0.15);
    background: white;
}

.splits-table th {
    background: linear-gradient(135deg, #1f2937, #374151);
    color: white;
    padding: 16px 12px;
    text-align: center;
    font-weight: 700;
    font-size: 0.9em;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    border: none;
}

.splits-table td {
    padding: 12px 10px;
    text-align: center;
    border: 1px solid #d1d5db;
    font-weight: 500;
    font-size: 0.9em;
}

/* MUCH DARKER alternating rows for better visibility */
.splits-table tr:nth-child(even) {
    background-color: #9ca3af; /* MUCH DARKER GRAY */
    color: #1f2937;
}

.splits-table tr:nth-child(odd) {
    background-color: #ffffff;
}

.splits-table tr:hover {
    background-color: #6b7280 !important; /* DARK HOVER */
    color: white !important;
    transform: scale(1.01);
    transition: all 0.2s ease;
}

/* Progressive Disclosure - IMPROVED STYLING */
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
        grid-template-columns: 1fr; /* Single column on mobile */
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

    def generate_refined_markdown(self, data: Dict) -> str:
        """Generate refined markdown with smart layouts and HTML table"""
        content = []
        date = data.get('date', '')
        
        # Add comprehensive CSS
        content.append(self.get_comprehensive_css())
        content.append("")
        
        # Add navigation buttons
        nav_buttons = self.get_navigation_buttons(date)
        if nav_buttons:
            content.append(nav_buttons)
            content.append("")
        
        # Three-column card container
        content.append('<div class="card-container">')
        
        # Sleep Health Card - SMART METRIC LAYOUT
        content.append('<div class="metric-card sleep-card">')
        content.append('<div class="card-header"><span class="card-emoji">🛌</span>Sleep Health</div>')
        
        sleep = data.get('sleep_metrics', {})
        if any(v is not None for v in sleep.values()):
            if sleep.get('sleep_minutes'):
                hours = sleep['sleep_minutes'] // 60
                mins = sleep['sleep_minutes'] % 60
                content.append(f'<div class="metric-primary">{hours}h {mins}m total</div>')
            
            # Prepare metrics for smart layout
            sleep_metrics = []
            if sleep.get('sleep_score'):
                sleep_metrics.append({"label": "Score", "value": sleep["sleep_score"]})
            if sleep.get('hrv_night_avg'):
                sleep_metrics.append({"label": "HRV", "value": f"{sleep['hrv_night_avg']}ms"})
            
            content.append(self.get_smart_metric_layout(sleep_metrics))
            
            # IMPROVED Sleep breakdown
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

        # Daily Wellness Card - SMART METRIC LAYOUT
        content.append('<div class="metric-card wellness-card">')
        content.append('<div class="card-header"><span class="card-emoji">⚡</span>Daily Wellness</div>')
        
        daily = data.get('daily_metrics', {})
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

        # Workout Stats Card - SMART METRIC LAYOUT
        workouts = data.get('workout_metrics', [])
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

            # PROPER HTML TABLE for Splits
            splits = workout.get('splits', [])
            if splits:
                content.append('<div class="splits-section">')
                content.append('<h2>📊 Split Analysis</h2>')
                content.append(self.generate_html_table(splits))
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

    def update_file(self, file_path: Path) -> bool:
        """Update a single file with smart layouts and HTML table"""
        logger.info(f"Updating file: {file_path}")
        
        # Parse current YAML data
        data = self.parse_yaml_frontmatter(file_path)
        if not data:
            logger.error(f"Could not parse YAML from {file_path}")
            return False
        
        # Generate new refined markdown
        new_markdown = self.generate_refined_markdown(data)
        
        # Generate updated YAML frontmatter
        yaml_content = yaml.dump(data, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        # Generate JSON section
        json_content = json.dumps(data, indent=2)
        
        # Combine all sections
        full_content = f"""---
{yaml_content}---
{new_markdown}

<details>
<summary>📄 Full JSON Data</summary>

```json
{json_content}
```
</details>
"""
        
        # Write updated file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(full_content)
        
        logger.info(f"Successfully updated {file_path}")
        return True

    def get_files_to_update(self) -> List[Path]:
        """Get list of files from June 13 - July 9 to update"""
        files = []
        data_dir = Path("data/2025")
        
        # June files (13-30)
        june_dir = data_dir / "06"
        for day in range(13, 31):
            file_path = june_dir / f"{day:02d}.md"
            if file_path.exists():
                files.append(file_path)
        
        # July files (1-9)
        july_dir = data_dir / "07"
        for day in range(1, 10):
            file_path = july_dir / f"{day:02d}.md"
            if file_path.exists():
                files.append(file_path)
        
        logger.info(f"Found {len(files)} files to update")
        return files

    def run_final_layout_fix(self):
        """Execute final layout fixes on all target files"""
        logger.info("Starting final layout fixes...")
        
        # Get files to update
        files_to_update = self.get_files_to_update()
        if not files_to_update:
            logger.error("No files found to update")
            return False
        
        # Update each file
        updated_files = 0
        failed_files = 0
        
        for file_path in files_to_update:
            try:
                if self.update_file(file_path):
                    updated_files += 1
                else:
                    failed_files += 1
            except Exception as e:
                logger.error(f"Failed to update {file_path}: {e}")
                failed_files += 1
        
        logger.info(f"Final layout fixes completed:")
        logger.info(f"  Successfully updated: {updated_files} files")
        logger.info(f"  Failed to update: {failed_files} files")
        
        return failed_files == 0

def main():
    """Main entry point"""
    try:
        fixer = FinalLayoutFixer()
        success = fixer.run_final_layout_fix()
        if success:
            logger.info("Final layout fixes completed successfully!")
        else:
            logger.error("Final layout fixes encountered errors")
            exit(1)
    except Exception as e:
        logger.error(f"Final layout fixes failed: {e}")
        exit(1)

if __name__ == "__main__":
    main() 