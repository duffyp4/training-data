#!/usr/bin/env python3
"""
Generate Enhanced Index
Creates a modern training data dashboard with quick stats, interactive calendar, and Nike training plan progress
"""

import os
import yaml
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Tuple
import logging
import calendar

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def extract_full_data_from_file(file_path: Path) -> Dict:
    """Extract comprehensive data from a daily file including sleep and wellness metrics"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Extract YAML front matter
        if content.startswith('---'):
            end_yaml = content.find('---', 3)
            if end_yaml != -1:
                yaml_content = content[3:end_yaml]
                data = yaml.safe_load(yaml_content)
                
                # Calculate workout metrics
                workouts = data.get('workout_metrics', [])
                total_distance = sum(w.get('distance_mi', 0) for w in workouts)
                total_time_s = sum(w.get('moving_time_s', 0) for w in workouts)
                workout_count = len(workouts)
                
                # Check for wellness data
                sleep_metrics = data.get('sleep_metrics', {})
                daily_metrics = data.get('daily_metrics', {})
                has_wellness = bool(sleep_metrics or daily_metrics)
                
                # Get sleep score
                sleep_score = sleep_metrics.get('sleep_score') if sleep_metrics else None
                
                return {
                    'date': data.get('date'),
                    'workout_count': workout_count,
                    'total_distance': total_distance,
                    'total_time_s': total_time_s,
                    'has_wellness': has_wellness,
                    'sleep_score': sleep_score,
                    'file_path': str(file_path)
                }
    except Exception as e:
        logger.warning(f"Could not parse {file_path}: {e}")
    
    return None

def generate_current_month_stats(daily_files: List[Dict]) -> str:
    """Generate quick stats dashboard for current month"""
    current_month = datetime.now().strftime('%Y-%m')
    current_month_files = [f for f in daily_files if f['date'].startswith(current_month)]
    
    # Calculate stats
    total_workouts = sum(f['workout_count'] for f in current_month_files)
    total_miles = sum(f['total_distance'] for f in current_month_files)
    total_hours = sum(f['total_time_s'] for f in current_month_files) / 3600
    
    # Calculate average sleep score
    sleep_scores = [f['sleep_score'] for f in current_month_files if f['sleep_score'] is not None]
    avg_sleep_score = sum(sleep_scores) / len(sleep_scores) if sleep_scores else 0
    
    month_name = datetime.now().strftime('%B %Y')
    
    html = f'''
<div class="stats-dashboard">
    <h2>📊 {month_name} Quick Stats</h2>
    <div class="stats-grid">
        <div class="stat-card">
            <div class="stat-number">{total_workouts}</div>
            <div class="stat-label">Total Workouts</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{total_miles:.1f}</div>
            <div class="stat-label">Miles</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{total_hours:.1f}</div>
            <div class="stat-label">Hours</div>
        </div>
        <div class="stat-card">
            <div class="stat-number">{avg_sleep_score:.0f}</div>
            <div class="stat-label">Avg Sleep Score</div>
        </div>
    </div>
</div>
'''
    return html

def generate_calendar_widget(daily_files: List[Dict]) -> str:
    """Generate interactive calendar with workout/wellness indicators"""
    # Create lookup for existing dates
    date_lookup = {}
    for file_data in daily_files:
        date_obj = datetime.strptime(file_data['date'], '%Y-%m-%d')
        date_lookup[date_obj] = file_data
    
    # Get current month info
    now = datetime.now()
    year = now.year
    month = now.month
    month_name = now.strftime('%B %Y')
    
    # Get calendar for current month (Sunday first)
    calendar.setfirstweekday(calendar.SUNDAY)
    cal = calendar.monthcalendar(year, month)
    
    html = [f'''
<div class="calendar-widget">
    <h2>📅 Calendar Navigator</h2>
    <div class="calendar-header">
        <button class="calendar-nav" onclick="changeMonth(-1)">‹</button>
        <h3 id="calendar-month">{month_name}</h3>
        <button class="calendar-nav" onclick="changeMonth(1)">›</button>
    </div>
    <div class="calendar-grid">
        <div class="calendar-day-header">Sun</div>
        <div class="calendar-day-header">Mon</div>
        <div class="calendar-day-header">Tue</div>
        <div class="calendar-day-header">Wed</div>
        <div class="calendar-day-header">Thu</div>
        <div class="calendar-day-header">Fri</div>
        <div class="calendar-day-header">Sat</div>
''']
    
    # Generate calendar days
    for week in cal:
        for day in week:
            if day == 0:
                html.append('        <div class="calendar-day empty"></div>')
            else:
                date_obj = datetime(year, month, day)
                file_data = date_lookup.get(date_obj)
                
                if file_data:
                    has_workout = file_data['workout_count'] > 0
                    has_wellness = file_data['has_wellness']
                    
                    dots = []
                    if has_workout:
                        dots.append('<span class="dot workout-dot">🟢</span>')
                    if has_wellness:
                        dots.append('<span class="dot wellness-dot">🔵</span>')
                    
                    dots_html = ''.join(dots)
                    # Convert .md path to HTML path for GitHub Pages
                    file_path = file_data['file_path'].replace('\\', '/').replace('.md', '.html')
                    
                    html.append(f'        <div class="calendar-day has-data" onclick="window.location.href=\'{file_path}\'">')
                    html.append(f'            <span class="day-number">{day}</span>')
                    html.append(f'            <div class="day-dots">{dots_html}</div>')
                    html.append('        </div>')
                else:
                    html.append(f'        <div class="calendar-day">')
                    html.append(f'            <span class="day-number">{day}</span>')
                    html.append('        </div>')
    
    html.append('''    </div>
    <div class="calendar-legend">
        <span><span class="dot">🟢</span> Workout Data</span>
        <span><span class="dot">🔵</span> Wellness Data</span>
    </div>
</div>''')
    
    return '\n'.join(html)

def generate_weekly_training_cards(daily_files: List[Dict]) -> str:
    """Generate weekly training summary cards with Hal Higdon targets"""
    try:
        # Load Hal Higdon training plan
        with open('nike_training_plan.json', 'r') as f:
            plan = json.load(f)
        
        # Start from June 8, 2025 (Week 1)
        start_date = datetime(2025, 6, 8)  # Sunday, June 8th
        
        html = ['''
<div class="training-plan">
    <h2>🏃‍♂️ Weekly Training vs Hal Higdon Novice 2</h2>
    <div class="training-cards">''']
        
        week_num = 1
        current_week_start = start_date
        
        while current_week_start <= datetime.now() and week_num <= len(plan['weeks']):
            week_end = current_week_start + timedelta(days=6)
            
            # Calculate actual miles for this week
            week_files = [f for f in daily_files 
                         if current_week_start.strftime('%Y-%m-%d') <= f['date'] <= week_end.strftime('%Y-%m-%d')]
            
            actual_miles = sum(f['total_distance'] for f in week_files)
            workout_count = sum(f['workout_count'] for f in week_files)
            
            # Get target from Hal Higdon plan
            target_miles = plan['weeks'][week_num-1]['target_miles']
            
            # Determine status based on target achievement and week completion
            if week_end < datetime.now():
                # Completed week - check if target was hit
                if actual_miles >= target_miles:
                    status_class = 'hit-target'
                    status_icon = '✅'
                else:
                    status_class = 'missed-target'
                    status_icon = '❌'
            else:
                # Current week in progress
                status_class = 'current-week'
                status_icon = '🔄'
            
            # Format date range
            week_start_str = current_week_start.strftime('%b %d')
            week_end_str = week_end.strftime('%b %d')
            
            html.append(f'''
        <div class="training-card {status_class}">
            <div class="training-card-header">
                <h4>Week {week_num}</h4>
                <span class="status-icon">{status_icon}</span>
            </div>
            <div class="training-card-content">
                <div class="week-dates">{week_start_str} - {week_end_str}</div>
                <div class="mileage-comparison">
                    <span class="actual-miles">{actual_miles:.1f} miles</span>
                    <span class="target-miles">Target: {target_miles} miles</span>
                </div>
                <div class="week-stats">
                    <div class="stat-item">
                        <span class="stat-number">{workout_count}</span>
                        <span class="stat-label">workouts</span>
                    </div>
                </div>
            </div>
        </div>''')
            
            week_num += 1
            current_week_start += timedelta(weeks=1)
        
        html.append('''    </div>
</div>''')
        
        return '\n'.join(html)
        
    except Exception as e:
        logger.error(f"Error generating weekly training cards: {e}")
        return '<div class="training-plan"><h2>🏃‍♂️ Weekly Training</h2><p>Error loading training data.</p></div>'

def generate_enhanced_index():
    """Generate the new enhanced index.md"""
    data_dir = Path('data')
    
    # Find all daily files
    daily_files = []
    for year_dir in sorted(data_dir.glob('20*')):
        if year_dir.is_dir():
            for month_dir in sorted(year_dir.glob('*')):
                if month_dir.is_dir():
                    for day_file in sorted(month_dir.glob('*.md')):
                        file_data = extract_full_data_from_file(day_file)
                        if file_data:
                            daily_files.append(file_data)
    
    # Sort by date (newest first for JSON, but we'll use chronologically for processing)
    daily_files.sort(key=lambda x: x['date'])
    
    logger.info(f"Found {len(daily_files)} daily files")
    
    # Generate new index content
    content = []
    content.append('<link rel="stylesheet" href="training-data.css">')
    content.append('')
    content.append('# 🏃‍♂️ Training Data Dashboard')
    content.append('')
    content.append('Comprehensive training data with detailed per-split metrics, workout data, and wellness information.')
    content.append('')
    
    # Add Quick Stats Dashboard
    content.append(generate_current_month_stats(daily_files))
    content.append('')
    
    # Add Calendar Widget
    content.append(generate_calendar_widget(daily_files))
    content.append('')
    
    # Add Weekly Training Cards
    content.append(generate_weekly_training_cards(daily_files))
    content.append('')
    
    # Add JavaScript for calendar functionality
    content.append('''
<script>
let currentMonth = new Date().getMonth();
let currentYear = new Date().getFullYear();

function changeMonth(delta) {
    currentMonth += delta;
    if (currentMonth > 11) {
        currentMonth = 0;
        currentYear++;
    } else if (currentMonth < 0) {
        currentMonth = 11;
        currentYear--;
    }
    
    const monthNames = ["January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"];
    
    document.getElementById('calendar-month').textContent = 
        monthNames[currentMonth] + ' ' + currentYear;
    
    // Note: Full calendar regeneration would require server-side update
    // For now, this updates the header. Full implementation would require AJAX.
}
</script>''')
    
    # Write index.md
    index_content = '\n'.join(content)
    with open('index.md', 'w', encoding='utf-8') as f:
        f.write(index_content)
    
    # Create data/index.txt for AI agent consumption
    txt_data = []
    daily_files_for_txt = sorted(daily_files, key=lambda x: x['date'], reverse=True)
    
    for file_data in daily_files_for_txt:
        local_path = file_data['file_path'].replace('\\', '/')
        github_raw_url = f"https://raw.githubusercontent.com/duffyp4/training-data/main/{local_path}"
        
        txt_data.append(f"{file_data['date']}: {github_raw_url}")
    
    data_dir.mkdir(exist_ok=True)
    with open(data_dir / 'index.txt', 'w', encoding='utf-8') as f:
        f.write('\n'.join(txt_data))
    
    logger.info("Generated enhanced index.md and created data/index.txt")
    return len(daily_files)

def main():
    """Main entry point"""
    try:
        file_count = generate_enhanced_index()
        print(f"✅ Generated enhanced index.md with {file_count} daily files")
    except Exception as e:
        logger.error(f"Error generating enhanced index: {e}")
        exit(1)

if __name__ == "__main__":
    main()