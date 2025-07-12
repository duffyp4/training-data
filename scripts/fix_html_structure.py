#!/usr/bin/env python3
"""
Fix HTML structure issues in training data files.

This script:
1. Identifies files with broken HTML structure where card-container closes too early
2. Moves workout-detail-card and splits-section inside the card-container
3. Ensures proper grid layout for desktop centering
"""

import os
import re
from pathlib import Path

def find_html_files():
    """Find all .md files that use HTML format (newer files)."""
    data_dir = Path("data")
    html_files = []
    
    for year_dir in data_dir.iterdir():
        if not year_dir.is_dir():
            continue
            
        for month_dir in year_dir.iterdir():
            if not month_dir.is_dir():
                continue
                
            for file_path in month_dir.iterdir():
                if file_path.suffix == '.md':
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Check if it's an HTML format file
                            if '<div class="card-container">' in content and '<div class="splits-section">' in content:
                                html_files.append(file_path)
                    except Exception as e:
                        print(f"Warning: Could not read {file_path}: {e}")
    
    return sorted(html_files)

def analyze_html_structure(content):
    """Analyze the HTML structure to determine if it needs fixing."""
    # Look for the pattern where card-container closes before workout-detail-card
    
    # Find card-container opening
    card_container_start = content.find('<div class="card-container">')
    if card_container_start == -1:
        return "no_container"
    
    # Find the three metric cards (sleep, wellness, workout)
    sleep_card_pos = content.find('<div class="metric-card sleep-card">', card_container_start)
    wellness_card_pos = content.find('<div class="metric-card wellness-card">', sleep_card_pos)
    workout_card_pos = content.find('<div class="metric-card workout-card">', wellness_card_pos)
    
    if sleep_card_pos == -1 or wellness_card_pos == -1 or workout_card_pos == -1:
        return "missing_cards"
    
    # Find workout-detail-card and splits-section
    workout_detail_pos = content.find('<div class="workout-detail-card">')
    splits_section_pos = content.find('<div class="splits-section">')
    
    if workout_detail_pos == -1 or splits_section_pos == -1:
        return "missing_sections"
    
    # Find where card-container closes
    # We need to find the closing div that matches the card-container opening
    # Start searching after the workout card
    search_start = workout_card_pos
    
    # Count div openings and closings to find the matching close
    div_count = 1  # We already have the opening card-container
    pos = search_start
    
    while pos < len(content) and div_count > 0:
        # Find next div tag
        open_tag = content.find('<div', pos)
        close_tag = content.find('</div>', pos)
        
        if close_tag == -1:
            return "malformed_html"
        
        if open_tag != -1 and open_tag < close_tag:
            # Found opening div
            div_count += 1
            pos = open_tag + 4
        else:
            # Found closing div
            div_count -= 1
            if div_count == 0:
                # This is where card-container closes
                card_container_end = close_tag + 6  # Include the </div>
                break
            pos = close_tag + 6
    else:
        return "malformed_html"
    
    # Check if workout-detail-card and splits-section are after card-container closes
    if workout_detail_pos > card_container_end or splits_section_pos > card_container_end:
        return "broken_structure"
    else:
        return "correct_structure"

def fix_html_structure(content):
    """Fix the HTML structure by moving elements inside card-container."""
    
    # Find the positions of key elements
    card_container_start = content.find('<div class="card-container">')
    workout_detail_start = content.find('<div class="workout-detail-card">')
    splits_section_start = content.find('<div class="splits-section">')
    
    # Find the end of each section
    workout_detail_end = find_matching_div_close(content, workout_detail_start)
    splits_section_end = find_matching_div_close(content, splits_section_start)
    
    if workout_detail_end == -1 or splits_section_end == -1:
        return None
    
    # Extract the workout-detail-card and splits-section content
    workout_detail_content = content[workout_detail_start:workout_detail_end]
    splits_section_content = content[splits_section_start:splits_section_end]
    
    # Remove them from their current positions (remove from end first to preserve positions)
    if splits_section_end > workout_detail_end:
        # Remove splits section first
        content = content[:splits_section_start] + content[splits_section_end:]
        # Adjust workout detail end position
        workout_detail_end -= (splits_section_end - splits_section_start)
        content = content[:workout_detail_start] + content[workout_detail_end:]
    else:
        # Remove workout detail first
        content = content[:workout_detail_start] + content[workout_detail_end:]
        # Adjust splits section positions
        splits_section_start -= (workout_detail_end - workout_detail_start)
        splits_section_end -= (workout_detail_end - workout_detail_start)
        content = content[:splits_section_start] + content[splits_section_end:]
    
    # Find where to insert them inside card-container
    # Look for the last metric card's closing div
    workout_card_start = content.find('<div class="metric-card workout-card">')
    if workout_card_start == -1:
        return None
    
    workout_card_end = find_matching_div_close(content, workout_card_start)
    if workout_card_end == -1:
        return None
    
    # Insert the sections after the workout card but before card-container closes
    insertion_point = workout_card_end
    
    # Insert workout-detail-card and splits-section
    new_content = (
        content[:insertion_point] + 
        '\n' + workout_detail_content + 
        '\n' + splits_section_content + 
        '\n' + content[insertion_point:]
    )
    
    return new_content

def find_matching_div_close(content, start_pos):
    """Find the closing </div> that matches a <div> at start_pos."""
    if start_pos == -1:
        return -1
    
    # Find the end of the opening tag
    tag_end = content.find('>', start_pos)
    if tag_end == -1:
        return -1
    
    # Count nested divs
    div_count = 1
    pos = tag_end + 1
    
    while pos < len(content) and div_count > 0:
        # Find next div tag
        open_tag = content.find('<div', pos)
        close_tag = content.find('</div>', pos)
        
        if close_tag == -1:
            return -1
        
        if open_tag != -1 and open_tag < close_tag:
            # Found opening div
            div_count += 1
            pos = open_tag + 4
        else:
            # Found closing div
            div_count -= 1
            if div_count == 0:
                return close_tag + 6  # Include the </div>
            pos = close_tag + 6
    
    return -1

def main():
    """Main function to fix HTML structure."""
    print("🔍 Scanning for HTML format files...")
    html_files = find_html_files()
    
    print(f"📁 Found {len(html_files)} HTML format files")
    
    print("\n🔧 Analyzing HTML structure...")
    
    broken_files = []
    correct_files = []
    
    for file_path in html_files:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        structure_status = analyze_html_structure(content)
        
        if structure_status == "broken_structure":
            broken_files.append(file_path)
            print(f"  🔴 {file_path}: BROKEN - needs fixing")
        elif structure_status == "correct_structure":
            correct_files.append(file_path)
            print(f"  ✅ {file_path}: OK")
        else:
            print(f"  ⚠️  {file_path}: {structure_status}")
    
    print(f"\n📊 Summary:")
    print(f"  ✅ Correct structure: {len(correct_files)} files")
    print(f"  🔴 Broken structure: {len(broken_files)} files")
    
    if broken_files:
        print(f"\n🔧 Fixing {len(broken_files)} files with broken structure...")
        
        fixed_count = 0
        for file_path in broken_files:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            fixed_content = fix_html_structure(content)
            
            if fixed_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(fixed_content)
                fixed_count += 1
                print(f"  ✅ Fixed {file_path}")
            else:
                print(f"  ❌ Failed to fix {file_path}")
        
        print(f"\n🎉 Successfully fixed {fixed_count}/{len(broken_files)} files")
    else:
        print("\n🎉 All files already have correct structure!")

if __name__ == "__main__":
    main() 