#!/usr/bin/env python3

import os
import yaml
import json
import sys
from pathlib import Path
import re

# Add the scripts directory to path
sys.path.append(str(Path(__file__).parent))

# Import the updated formatting function
from add_structured_human_readable import generate_structured_readable

def update_file_formatting(filepath):
    """Update a single daily file with the new formatting (no API calls)"""
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
    
    # Generate new structured readable content
    structured_content = generate_structured_readable(data)
    
    # Find where to replace the structured content (between Sleep: line and Full JSON)
    full_json_pattern = r'<details>\s*\n<summary>Full JSON</summary>'
    match = re.search(full_json_pattern, markdown_content)
    
    if match:
        # Find the basic summary section
        lines = markdown_content[:match.start()].strip().split('\n')
        
        # Find the end of the basic summary (should contain "Sleep:")
        summary_end_idx = -1
        for i, line in enumerate(lines):
            if line.startswith('**Sleep:**') or 'Sleep:' in line:
                summary_end_idx = i
                break
        
        if summary_end_idx >= 0:
            # Keep everything up to and including the sleep line
            before_structured = '\n'.join(lines[:summary_end_idx + 1])
            
            # Add the new structured content
            json_section = markdown_content[match.start():]
            new_markdown = f"{before_structured}\n\n{structured_content}\n\n{json_section}"
        else:
            print(f"Warning: Could not find basic summary in {filepath}")
            return
    else:
        print(f"Warning: Could not find Full JSON section in {filepath}")
        return
    
    # Write updated content (no changes to YAML or JSON, just markdown formatting)
    updated_content = f"---\n{yaml_front_matter}---\n{new_markdown}"
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(updated_content)
    
    print(f"Updated formatting for {filepath}")

def main():
    """Process all daily markdown files to update formatting"""
    data_dir = 'data'
    
    files_to_process = []
    for root, dirs, files in os.walk(data_dir):
        for file in files:
            if file.endswith('.md') and file != 'index.md':
                filepath = os.path.join(root, file)
                files_to_process.append(filepath)
    
    # Sort files 
    files_to_process.sort()
    
    print(f"Found {len(files_to_process)} files to update")
    
    for i, filepath in enumerate(files_to_process):
        try:
            print(f"Processing file {i+1}/{len(files_to_process)}")
            update_file_formatting(filepath)
        except Exception as e:
            print(f"Error processing {filepath}: {e}")

if __name__ == "__main__":
    main() 