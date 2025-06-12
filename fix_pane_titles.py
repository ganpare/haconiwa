#!/usr/bin/env python3
"""Fix pane titles for haconiwa-dev-company session"""

import subprocess
import json
from pathlib import Path

def fix_pane_titles():
    """Fix all pane titles based on desk_mappings.json"""
    
    # Load desk mappings
    desk_mappings_file = Path("haconiwa-dev-world/.haconiwa/desk_mappings.json")
    if not desk_mappings_file.exists():
        print(f"Error: {desk_mappings_file} not found")
        return
    
    with open(desk_mappings_file, 'r') as f:
        mappings = json.load(f)
    
    session_name = "haconiwa-dev-company"
    
    # Process each mapping
    for idx, mapping in enumerate(mappings):
        agent_id = mapping.get('agent_id', f'agent-{idx}')
        
        # Calculate window and pane index
        if idx < 16:
            window_id = 0
            pane_index = idx
        else:
            window_id = 1
            pane_index = idx - 16
        
        # Check current directory for the pane
        cmd = ["tmux", "display-message", "-t", f"{session_name}:{window_id}.{pane_index}", 
               "-p", "#{pane_current_path}"]
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            current_path = result.stdout.strip()
            
            # Determine if it's a task or standby
            if "/tasks/task_" in current_path:
                # Extract task name from path
                task_name = current_path.split("/tasks/")[1].split("/")[0]
                title = f"{agent_id} - {task_name}"
            else:
                title = f"{agent_id} - standby"
            
            # Set pane title
            cmd = ["tmux", "select-pane", "-t", f"{session_name}:{window_id}.{pane_index}", 
                   "-T", title]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ Set title for pane {window_id}.{pane_index}: {title}")
            else:
                print(f"✗ Failed to set title for pane {window_id}.{pane_index}")
        else:
            print(f"✗ Could not get current path for pane {window_id}.{pane_index}")

if __name__ == "__main__":
    fix_pane_titles()