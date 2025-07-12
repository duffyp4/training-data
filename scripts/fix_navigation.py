#!/usr/bin/env python3
"""
Fix navigation links across all training data files.

This script:
1. Scans all existing .md files in the data directory
2. Creates a chronological list of available dates
3. Updates navigation links to point to the correct previous/next files
4. Handles missing dates by linking to the nearest available dates
"""

import os
import re
from datetime import datetime, timedelta
from pathlib import Path

def find_all_data_files():
    """Find all .md data files and return sorted list of (date, filepath) tuples."""
    data_dir = Path("data")
    files = []
    
    for year_dir in data_dir.iterdir():
        if not year_dir.is_dir():
            continue
            
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir():
                continue
                
            for file_path in month_dir.iterdir():
                if file_path.suffix == '.md':
                    # Extract date from filename and path
                    try:
                        year = int(year_dir.name)
                        month = int(month_dir.name)
                        day = int(file_path.stem)
                        date_obj = datetime(year, month, day)
                        files.append((date_obj, file_path))
                    except (ValueError, TypeError):
                        print(f"Warning: Could not parse date from {file_path}")
    
    # Sort by date
    files.sort(key=lambda x: x[0])
    return files

def create_navigation_html(current_date, prev_file=None, next_file=None):
    """Create navigation HTML for a given date."""
    # Format current date
    current_str = current_date.strftime("%B %d, %Y")
    
    # Previous button
    if prev_file:
        prev_date = prev_file[0]
        prev_path = get_relative_path(current_date, prev_date)
        prev_label = prev_date.strftime("%b %d")
        prev_html = f'<a href="{prev_path}" class="nav-button nav-prev">← {prev_label}</a>'
    else:
        prev_html = '<span class="nav-disabled">← Previous</span>'
    
    # Next button  
    if next_file:
        next_date = next_file[0]
        next_path = get_relative_path(current_date, next_date)
        next_label = next_date.strftime("%b %d")
        next_html = f'<a href="{next_path}" class="nav-button nav-next">{next_label} →</a>'
    else:
        next_html = '<span class="nav-disabled">Next →</span>'
    
    return f'<div class="navigation-bar">{prev_html}<span class="nav-current">{current_str}</span>{next_html}</div>'

def create_navigation_markdown(current_date, prev_file=None, next_file=None):
    """Create navigation in markdown format for older files."""
    # Format current date
    current_str = current_date.strftime("%B %d, %Y")
    
    # Previous button
    if prev_file:
        prev_date = prev_file[0]
        prev_path = get_relative_path(current_date, prev_date)
        prev_label = prev_date.strftime("%b %d")
        prev_md = f'[← {prev_label}]({prev_path})'
    else:
        prev_md = '← Previous'
    
    # Next button  
    if next_file:
        next_date = next_file[0]
        next_path = get_relative_path(current_date, next_date)
        next_label = next_date.strftime("%b %d")
        next_md = f'[{next_label} →]({next_path})'
    else:
        next_md = 'Next →'
    
    return f'\n**Navigation:** {prev_md} | **{current_str}** | {next_md}\n\n---\n'

def get_relative_path(from_date, to_date):
    """Get relative path between two dates."""
    if from_date.year == to_date.year and from_date.month == to_date.month:
        # Same month - just use day
        return f"{to_date.day:02d}"
    elif from_date.year == to_date.year:
        # Same year, different month
        return f"../{to_date.month:02d}/{to_date.day:02d}"
    else:
        # Different year
        return f"../../{to_date.year}/{to_date.month:02d}/{to_date.day:02d}"

def detect_file_format(content):
    """Detect whether file is HTML format (newer) or Markdown format (older)."""
    # Look for HTML elements that indicate new format
    if '<div class="navigation-bar">' in content or '<link rel="stylesheet"' in content:
        return 'html'
    elif content.strip().startswith('---') and '# 2025-' in content:
        return 'markdown'
    else:
        return 'unknown'

def update_file_navigation(file_path, new_nav_html, current_date, prev_file=None, next_file=None):
    """Update the navigation in a file, handling both HTML and Markdown formats."""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    file_format = detect_file_format(content)
    
    if file_format == 'html':
        # Handle HTML format files
        nav_pattern = r'<div class="navigation-bar">.*?</div>'
        
        if re.search(nav_pattern, content):
            # Replace existing navigation
            updated_content = re.sub(nav_pattern, new_nav_html, content)
        else:
            # Insert navigation after CSS link
            css_pattern = r'(<link rel="stylesheet" href="[^"]+">)\s*'
            match = re.search(css_pattern, content)
            if match:
                updated_content = content.replace(
                    match.group(0), 
                    match.group(0) + '\n\n' + new_nav_html + '\n\n'
                )
            else:
                print(f"Warning: Could not find insertion point for navigation in HTML file {file_path}")
                return False
    
    elif file_format == 'markdown':
        # Handle Markdown format files
        nav_md = create_navigation_markdown(current_date, prev_file, next_file)
        
        # Remove existing navigation if present
        nav_md_pattern = r'\n\*\*Navigation:\*\*.*?\n\n---\n'
        content = re.sub(nav_md_pattern, '', content)
        
        # Insert after the markdown header (after the main date/title)
        header_pattern = r'(# \d{4}-\d{2}-\d{2}.*?\n)'
        match = re.search(header_pattern, content)
        if match:
            updated_content = content.replace(
                match.group(0),
                match.group(0) + nav_md
            )
        else:
            print(f"Warning: Could not find insertion point for navigation in Markdown file {file_path}")
            return False
    
    else:
        print(f"Warning: Unknown file format for {file_path}")
        return False
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    return True

def main():
    """Main function to fix all navigation."""
    print("🔍 Scanning for all data files...")
    files = find_all_data_files()
    
    print(f"📁 Found {len(files)} files")
    for date_obj, file_path in files:
        print(f"  {date_obj.strftime('%Y-%m-%d')}: {file_path}")
    
    print("\n🔧 Updating navigation links...")
    
    updated_count = 0
    for i, (current_date, current_path) in enumerate(files):
        # Get previous and next files
        prev_file = files[i - 1] if i > 0 else None
        next_file = files[i + 1] if i < len(files) - 1 else None
        
        # Create navigation HTML
        nav_html = create_navigation_html(current_date, prev_file, next_file)
        
        # Update file
        if update_file_navigation(current_path, nav_html, current_date, prev_file, next_file):
            updated_count += 1
            print(f"  ✅ Updated {current_date.strftime('%Y-%m-%d')}")
        else:
            print(f"  ❌ Failed to update {current_date.strftime('%Y-%m-%d')}")
    
    print(f"\n🎉 Successfully updated navigation in {updated_count}/{len(files)} files")

if __name__ == "__main__":
    main() 