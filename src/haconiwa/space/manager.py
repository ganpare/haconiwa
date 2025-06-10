"""
Space Manager for Haconiwa v1.0 - 32 Pane Support
"""

import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging

from ..core.crd.models import SpaceCRD

logger = logging.getLogger(__name__)


class SpaceManagerError(Exception):
    """Space manager error"""
    pass


class SpaceManager:
    """Space manager with 32-pane and multi-room support - Singleton pattern"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SpaceManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.active_sessions = {}
            self.task_assignments = {}  # Direct task assignment storage: {assignee: task_info}
            SpaceManager._initialized = True
    
    def set_task_assignments(self, task_assignments: Dict[str, Dict[str, Any]]):
        """Set task assignments for agent-to-task mapping"""
        self.task_assignments = task_assignments
        logger.info(f"Set {len(task_assignments)} task assignments in SpaceManager")
    
    def get_task_by_assignee(self, assignee: str) -> Dict[str, Any]:
        """Get task assigned to specific agent"""
        return self.task_assignments.get(assignee)
    
    def create_multiroom_session(self, config: Dict[str, Any]) -> bool:
        """Create multiroom tmux session with proper Room → Window mapping and task-centric directory structure"""
        try:
            session_name = config["name"]
            grid = config.get("grid", "8x4")
            base_path = Path(config.get("base_path", f"./{session_name}"))
            rooms = config.get("rooms", [])
            organizations = config.get("organizations", [])
            
            logger.info(f"Creating multiroom session: {session_name} with {len(rooms)} rooms")
            
            # Check and remove existing tmux session if it exists
            self._cleanup_existing_session(session_name)
            
            # Create base directory structure
            base_path.mkdir(parents=True, exist_ok=True)
            
            # Create tasks directory for Git repository and worktrees
            tasks_path = base_path / "tasks"
            tasks_path.mkdir(exist_ok=True)
            main_repo_path = tasks_path / "main"
            
            # Handle Git repository setup in tasks/main/
            if config.get("git_repo"):
                git_config = config["git_repo"]
                logger.info(f"Setting up Git repository in tasks/main/: {git_config['url']}")
                
                # Clone to tasks/main/ 
                force_clone = getattr(self, '_force_clone', False)
                success = self._clone_repository_to_tasks(git_config, main_repo_path, force_clone)
                if not success:
                    logger.warning("Failed to set up Git repository in tasks/main/, continuing without Git")
            
            # Generate desk mappings with organization info
            desk_mappings = self.generate_desk_mappings(organizations)
            
            # Create tmux session (initial window 0)
            self._create_tmux_session(session_name)
            
            # Configure pane borders and titles (same as company build)
            self._configure_pane_borders(session_name)
            
            # Create windows for each room
            if not self._create_windows_for_rooms(session_name, rooms):
                logger.error("Failed to create windows for rooms")
                return False
            
            # Distribute desks to windows
            desk_distribution = self._distribute_desks_to_windows(desk_mappings)
            
            # Debug: Log distribution details
            logger.info(f"Desk distribution summary:")
            for room_id, desks in desk_distribution.items():
                logger.info(f"  {room_id}: {len(desks)} mappings")
                for i, desk in enumerate(desks):
                    logger.info(f"    {i}: {desk['desk_id']} ({desk['role']}) -> {desk['title']}")
            
            # Calculate panes per window
            layout_info = self._calculate_panes_per_window(grid, len(rooms))
            panes_per_window = layout_info["panes_per_window"]
            
            # Create panes in each window and set up desks
            for room_id, desks_in_room in desk_distribution.items():
                window_id = self._get_window_id_for_room(room_id)
                
                # Get pane count for this specific room
                if isinstance(panes_per_window, dict):
                    room_pane_count = panes_per_window.get(room_id, 16)
                else:
                    room_pane_count = panes_per_window
                
                logger.info(f"Setting up {room_id}: {room_pane_count} panes, {len(desks_in_room)} mappings")
                
                # Create panes in this window
                if not self._create_panes_in_window(session_name, window_id, room_pane_count):
                    logger.warning(f"Failed to create panes in window {window_id}")
                    continue
                
                # Ensure we have enough mappings for the panes
                if len(desks_in_room) < room_pane_count:
                    logger.warning(f"Insufficient mappings for {room_id}: {len(desks_in_room)} mappings for {room_pane_count} panes")
                    continue
                elif len(desks_in_room) > room_pane_count:
                    logger.info(f"Extra mappings for {room_id}, using first {room_pane_count} mappings")
                    desks_in_room = desks_in_room[:room_pane_count]
                
                # Set up each desk in the window
                for pane_index, desk_mapping in enumerate(desks_in_room):
                    if pane_index >= room_pane_count:
                        logger.warning(f"Skipping extra mapping {pane_index} for {room_id}")
                        break
                    
                    desk_dir = self._create_desk_directory(base_path, desk_mapping)
                    self._update_pane_in_window(session_name, window_id, pane_index, desk_mapping, desk_dir)
            
            # Store session configuration
            self.active_sessions[session_name] = {
                "config": config,
                "base_path": str(base_path),
                "desk_mappings": desk_mappings,
                "desk_distribution": desk_distribution,
                "session_name": session_name
            }
            
            # Display created directory structure
            self._display_created_structure(base_path, organizations)
            
            logger.info(f"✅ Multiroom session '{session_name}' created successfully")
            logger.info(f"   📁 Base directory: {base_path}")
            logger.info(f"   🏢 Organizations: {len(organizations)}")
            logger.info(f"   🚪 Rooms: {len(rooms)} (Alpha & Beta)")
            logger.info(f"   🖥️ Panes: 32 (16 per room)")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to create multiroom session {config.get('name', 'unknown')}: {e}")
            return False
    
    def generate_desk_mappings(self, organizations: List[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Generate desk mappings for multi-room layout with Executive floor"""
        if not organizations:
            # Fallback to default organization names
            organizations = [
                {"id": "01", "name": "Frontend Development Team", "department_id": "frontend"},
                {"id": "02", "name": "Backend Development Team", "department_id": "backend"},
                {"id": "03", "name": "DevOps Infrastructure Team", "department_id": "devops"},
                {"id": "04", "name": "Quality Assurance Team", "department_id": "qa"},
                {"id": "05", "name": "Executive Leadership", "department_id": "executive"}
            ]
        
        mappings = []
        
        # Ensure we have at least 5 organizations
        while len(organizations) < 5:
            org_id = f"{len(organizations) + 1:02d}"
            organizations.append({"id": org_id, "name": f"Organization {len(organizations) + 1}", "department_id": "unknown"})
        
        # Room-01 (Alpha Room) - Organizations 1-2
        for i, org in enumerate(organizations[:2]):  # First 2 organizations
            org_id = i + 1
            org_name = org.get("name", f"Org-{org_id:02d}")
            
            for role_id in range(4):  # pm, worker-a, worker-b, worker-c
                desk_id = f"desk-{org_id:02d}{role_id:02d}"
                role_name = "pm" if role_id == 0 else f"worker-{chr(ord('a') + role_id - 1)}"
                
                # Directory naming: 01pm, 01a, 01b, 01c
                if role_name == "pm":
                    dir_name = f"{org_id:02d}pm"
                else:
                    worker_suffix = role_name.split("-")[1]  # a, b, c
                    dir_name = f"{org_id:02d}{worker_suffix}"
                
                # Create title with organization name
                role_display = "PM" if role_name == "pm" else role_name.upper()
                title = f"{org_name} - {role_display} - Alpha Room"
                
                mappings.append({
                    "desk_id": desk_id,
                    "org_id": f"org-{org_id:02d}",
                    "role": role_name,
                    "room_id": "room-01",
                    "directory_name": dir_name,
                    "title": title
                })
        
        # Room-02 (Beta Room) - Organizations 3-4
        for i, org in enumerate(organizations[2:4]):  # Organizations 3-4
            org_id = i + 3
            org_name = org.get("name", f"Org-{org_id:02d}")
            
            for role_id in range(4):  # pm, worker-a, worker-b, worker-c
                desk_id = f"desk-{org_id:02d}{role_id:02d}"
                role_name = "pm" if role_id == 0 else f"worker-{chr(ord('a') + role_id - 1)}"
                
                # Directory naming: 03pm, 03a, 03b, 03c, 04pm, 04a, 04b, 04c
                if role_name == "pm":
                    dir_name = f"{org_id:02d}pm"
                else:
                    worker_suffix = role_name.split("-")[1]  # a, b, c
                    dir_name = f"{org_id:02d}{worker_suffix}"
                
                # Create title with organization name
                role_display = "PM" if role_name == "pm" else role_name.upper()
                title = f"{org_name} - {role_display} - Beta Room"
                
                mappings.append({
                    "desk_id": desk_id,
                    "org_id": f"org-{org_id:02d}",
                    "role": role_name,
                    "room_id": "room-02",
                    "directory_name": dir_name,
                    "title": title
                })
        
        # Executive Room - Organization 5 (Executive Leadership)
        if len(organizations) >= 5:
            org = organizations[4]  # 5th organization (Executive)
            org_id = 5
            org_name = org.get("name", "Executive Leadership")
            
            logger.info(f"Generating Executive Room mappings for: {org_name}")
            
            # CEO, CTO, COO (3 executives + 1 assistant)
            executive_roles = ["ceo", "cto", "coo", "assistant"]
            executive_titles = ["CEO", "CTO", "COO", "Executive Assistant"]
            
            for role_id, (role_name, role_title) in enumerate(zip(executive_roles, executive_titles)):
                desk_id = f"desk-exec-{role_id:02d}"
                
                # Directory naming: exec-ceo, exec-cto, exec-coo, exec-assistant
                dir_name = f"exec-{role_name}"
                
                # Create title with executive role
                title = f"{org_name} - {role_title} - Executive Room"
                
                mapping = {
                    "desk_id": desk_id,
                    "org_id": f"org-05",
                    "role": role_name,
                    "room_id": "room-executive",
                    "directory_name": dir_name,
                    "title": title
                }
                
                logger.debug(f"Generated Executive mapping {role_id}: {mapping}")
                mappings.append(mapping)
            
            logger.info(f"Generated {len(executive_roles)} Executive Room mappings")
        
        logger.info(f"Total mappings generated: {len(mappings)}")
        return mappings
    
    def convert_crd_to_config(self, crd: SpaceCRD) -> Dict[str, Any]:
        """Convert Space CRD to internal configuration"""
        # Navigate through the CRD structure to get company config
        company = crd.spec.nations[0].cities[0].villages[0].companies[0]
        
        # Use world name as base path if basePath is not specified
        base_path = company.basePath
        if base_path is None:
            base_path = f"./{crd.metadata.name}"
        
        config = {
            "name": company.name,
            "grid": company.grid,
            "base_path": base_path,
            "git_repo": None,
            "organizations": [],
            "rooms": [
                {"id": "room-01", "name": "Alpha Room"},
                {"id": "room-02", "name": "Beta Room"},
                {"id": "room-executive", "name": "Executive Room"}
            ]
        }
        
        # Add git repository config if specified
        if company.gitRepo:
            config["git_repo"] = {
                "url": company.gitRepo.url,
                "default_branch": company.gitRepo.defaultBranch,
                "auth": company.gitRepo.auth
            }
        
        # Get organization reference and fetch organization data
        organization_ref = getattr(company, 'organizationRef', None)
        if organization_ref:
            # Fetch organization data from applied Organization CRDs
            organizations = self._get_organization_data(organization_ref)
            config["organizations"] = organizations
        else:
            # Fallback to default organizations if no organizationRef
            logger.warning("No organizationRef found, using default organizations")
            config["organizations"] = [
                {"id": "01", "name": "Frontend Development Team", "department_id": "frontend"},
                {"id": "02", "name": "Backend Development Team", "department_id": "backend"},
                {"id": "03", "name": "DevOps Infrastructure Team", "department_id": "devops"},
                {"id": "04", "name": "Quality Assurance Team", "department_id": "qa"},
                {"id": "05", "name": "Executive Leadership", "department_id": "executive"}
            ]
        
        return config
    
    def _get_organization_data(self, organization_ref: str) -> List[Dict[str, Any]]:
        """Get organization data from applied Organization CRDs"""
        try:
            logger.info(f"Fetching organization data for ref: {organization_ref}")
            
            # Try to get the actual Organization CRD from applied resources
            from ..core.applier import CRDApplier
            
            # Get singleton instance of CRDApplier - this needs to be improved in real implementation
            # For now, we'll use a workaround to access applied resources
            
            # Search for applied Organization CRD
            organization_crd = None
            applied_resources = {}
            
            # Try to access via module-level variable (workaround)
            try:
                import sys
                if hasattr(sys.modules.get('__main__'), '_current_applier'):
                    applier = getattr(sys.modules['__main__'], '_current_applier')
                    applied_resources = applier.get_applied_resources()
            except:
                pass
            
            # Look for Organization CRD in applied resources
            for resource_key, resource in applied_resources.items():
                if resource_key.startswith("Organization/") and resource.metadata.name == organization_ref:
                    organization_crd = resource
                    logger.info(f"Found Organization CRD: {organization_ref}")
                    break
            
            if organization_crd:
                # Map Organization CRD departments to 32-pane structure (4 orgs × 4 roles × 2 rooms)
                departments = organization_crd.spec.hierarchy.departments
                logger.info(f"Found {len(departments)} departments in Organization CRD")
                
                # Create organization mapping based on departments
                organizations = []
                
                # Map departments to 4 organizations for 32-pane layout
                department_mapping = [
                    ("frontend", "Frontend Development Team"),
                    ("backend", "Backend Development Team"), 
                    ("devops", "DevOps Infrastructure Team"),
                    ("qa", "Quality Assurance Team"),
                    ("executive", "Executive Leadership")  # 5番目の組織として追加
                ]
                
                for i, (dept_id, default_name) in enumerate(department_mapping):
                    org_id = f"{i+1:02d}"
                    
                    # Find matching department in Organization CRD
                    dept_name = default_name
                    for dept in departments:
                        if dept.id == dept_id:
                            dept_name = dept.name
                            logger.info(f"Mapped department {dept_id} → {dept_name}")
                            break
                    
                    organizations.append({
                        "id": org_id,
                        "name": dept_name,
                        "department_id": dept_id
                    })
                
                # If we have executive department, map it to all organizations (leadership structure)
                executive_dept = None
                for dept in departments:
                    if dept.id == "executive":
                        executive_dept = dept
                        break
                
                if executive_dept:
                    logger.info(f"Found executive department: {executive_dept.name}")
                    # Executive roles will be distributed across organizations
                
                logger.info(f"Created {len(organizations)} organization mappings from Organization CRD")
                for org in organizations:
                    logger.info(f"  {org['id']}: {org['name']} (dept: {org['department_id']})")
                
                return organizations
                
            else:
                logger.warning(f"Organization CRD {organization_ref} not found in applied resources")
                # Fallback to enhanced default based on common department structure
                logger.info("Using enhanced default organization mapping")
                return [
                    {"id": "01", "name": "Frontend Development Team", "department_id": "frontend"},
                    {"id": "02", "name": "Backend Development Team", "department_id": "backend"},
                    {"id": "03", "name": "DevOps Infrastructure Team", "department_id": "devops"},
                    {"id": "04", "name": "Quality Assurance Team", "department_id": "qa"},
                    {"id": "05", "name": "Executive Leadership", "department_id": "executive"}
                ]
            
        except Exception as e:
            logger.error(f"Failed to get organization data for {organization_ref}: {e}")
            # Fallback to default organizations
            return [
                {"id": "01", "name": "Frontend Development Team", "department_id": "frontend"},
                {"id": "02", "name": "Backend Development Team", "department_id": "backend"},
                {"id": "03", "name": "DevOps Infrastructure Team", "department_id": "devops"},
                {"id": "04", "name": "Quality Assurance Team", "department_id": "qa"},
                {"id": "05", "name": "Executive Leadership", "department_id": "executive"}
            ]
    
    def _create_tmux_session(self, session_name: str):
        """Create tmux session"""
        cmd = ["tmux", "new-session", "-d", "-s", session_name]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise SpaceManagerError(f"Failed to create tmux session: {result.stderr}")
    
    def _create_windows_for_rooms(self, session_name: str, rooms: List[Dict[str, Any]]) -> bool:
        """Create tmux windows for each room"""
        try:
            for i, room in enumerate(rooms):
                room_name = room.get("name", f"Room {i+1}")
                window_name = room_name.replace(" Room", "")  # "Alpha Room" → "Alpha"
                
                if i == 0:
                    # Rename the initial window (window 0)
                    cmd = ["tmux", "rename-window", "-t", f"{session_name}:0", window_name]
                else:
                    # Create new window
                    cmd = ["tmux", "new-window", "-t", session_name, "-n", window_name]
                
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.error(f"Failed to create window {i} ({window_name}): {result.stderr}")
                    return False
                
                logger.info(f"Created window {i}: {window_name}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error creating windows for rooms: {e}")
            return False
    
    def _create_panes_in_window(self, session_name: str, window_id: str, pane_count: int) -> bool:
        """Create panes in specific tmux window - supports different layouts"""
        try:
            if pane_count == 4:
                # Executive Room layout: 1x4 (4 panes in a row)
                # Split horizontally 3 times to create 4 columns
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.0"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split 1 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.0"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split 2 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.1"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split 3 in window {window_id}: {result.stderr}")
                
                logger.info(f"Created {pane_count} panes in window {window_id} (1x4 Executive layout)")
                return True
                
            elif pane_count == 8:
                # Alpha/Beta Room layout: 2x4 (8 panes)
                # Split vertically once to create 2 rows
                cmd = ["tmux", "split-window", "-v", "-t", f"{session_name}:{window_id}.0"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create vertical split in window {window_id}: {result.stderr}")
                
                # Split each row horizontally 3 times to create 4 columns
                # Top row (panes 0-3)
                for i in range(3):
                    target_pane = 0 if i == 0 else 1
                    cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.{target_pane}"]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        logger.warning(f"Failed to create horizontal split top-{i+1} in window {window_id}: {result.stderr}")
                
                # Bottom row (panes 4-7)
                for i in range(3):
                    target_pane = 4 if i == 0 else 5
                    cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.{target_pane}"]
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        logger.warning(f"Failed to create horizontal split bottom-{i+1} in window {window_id}: {result.stderr}")
                
                # Apply tiled layout for even distribution
                cmd = ["tmux", "select-layout", "-t", f"{session_name}:{window_id}", "tiled"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to apply tiled layout to window {window_id}: {result.stderr}")
                
                logger.info(f"Created {pane_count} panes in window {window_id} (2x4 layout)")
                return True
                
            else:
                # Default 4x4 layout (16 panes) - existing logic
                # Split vertically 3 times to create 4 rows
                cmd = ["tmux", "split-window", "-v", "-t", f"{session_name}:{window_id}.0"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create vertical split 1 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-v", "-t", f"{session_name}:{window_id}.0"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create vertical split 2 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-v", "-t", f"{session_name}:{window_id}.1"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create vertical split 3 in window {window_id}: {result.stderr}")
                
                # Split each row horizontally 3 times to create 4 columns
                # Row 1 (panes 0-3)
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.0"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row1-1 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.0"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row1-2 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.1"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row1-3 in window {window_id}: {result.stderr}")
                
                # Row 2 (panes 4-7)
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.4"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row2-1 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.4"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row2-2 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.5"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row2-3 in window {window_id}: {result.stderr}")
                
                # Row 3 (panes 8-11)
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.8"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row3-1 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.8"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row3-2 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.9"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row3-3 in window {window_id}: {result.stderr}")
                
                # Row 4 (panes 12-15)
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.12"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row4-1 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.12"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row4-2 in window {window_id}: {result.stderr}")
                
                cmd = ["tmux", "split-window", "-h", "-t", f"{session_name}:{window_id}.13"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to create horizontal split row4-3 in window {window_id}: {result.stderr}")
                
                # Apply tiled layout for even distribution
                cmd = ["tmux", "select-layout", "-t", f"{session_name}:{window_id}", "tiled"]
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    logger.warning(f"Failed to apply tiled layout to window {window_id}: {result.stderr}")
                
                logger.info(f"Created {pane_count} panes in window {window_id} (4x4 layout)")
                return True
            
        except Exception as e:
            logger.error(f"Failed to create panes in window {window_id}: {e}")
            return False
    
    def _distribute_desks_to_windows(self, desk_mappings: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Distribute desk mappings to windows based on room_id"""
        distribution = {}
        
        for mapping in desk_mappings:
            room_id = mapping["room_id"]
            if room_id not in distribution:
                distribution[room_id] = []
            
            # Add window_id to mapping
            window_id = self._get_window_id_for_room(room_id)
            mapping_with_window = mapping.copy()
            mapping_with_window["window_id"] = window_id
            
            distribution[room_id].append(mapping_with_window)
        
        return distribution
    
    def _create_desk_directory(self, base_path: Path, mapping: Dict[str, Any]) -> Path:
        """Return base path without creating organization directories (agents will go to tasks or standby)"""
        # No longer create organization directories - agents go directly to tasks/ or standby/
        return base_path
    
    def _get_agent_id_from_pane_mapping(self, mapping: Dict[str, Any]) -> str:
        """Generate agent ID from pane mapping for task assignment lookup"""
        org_id = mapping["org_id"]  # "org-01"
        role = mapping["role"]      # "pm", "worker-a", "worker-b", "worker-c", "ceo", "cto", "coo", "assistant"
        room_id = mapping["room_id"]  # "room-01", "room-02", "room-executive"
        
        # Extract organization number
        org_num = org_id.split("-")[1]  # "01"
        
        # Convert role to agent format
        if role == "pm":
            role_part = "pm"
        elif role in ["ceo", "cto", "coo", "assistant"]:
            # Executive roles keep their original names
            role_part = role
        else:
            # "worker-a" → "wk-a"
            worker_suffix = role.split("-")[1]  # "a", "b", "c"
            role_part = f"wk-{worker_suffix}"
        
        # Convert room to agent format
        if room_id == "room-01":
            room_part = "r1"
        elif room_id == "room-02":
            room_part = "r2"
        elif room_id == "room-executive":
            room_part = "re"
        else:
            room_part = "r1"  # Default fallback
        
        # Generate agent ID: org01-pm-r1, org01-wk-a-r2, org05-ceo-re, etc.
        agent_id = f"org{org_num}-{role_part}-{room_part}"
        return agent_id
    
    def _get_task_directory_for_agent(self, agent_id: str, base_path: Path) -> Optional[Path]:
        """Get task worktree directory for assigned agent"""
        # Get task assignment for this agent
        task_info = self.get_task_by_assignee(agent_id)
        
        if task_info:
            # Return path to task worktree directory
            worktree_path = base_path / task_info["worktree_path"]
            if worktree_path.exists():
                logger.debug(f"Agent {agent_id} assigned to task {task_info['name']} → {worktree_path}")
                return worktree_path
            else:
                logger.warning(f"Task worktree directory not found: {worktree_path}")
        
        return None
    
    def _update_pane_in_window(self, session_name: str, window_id: str, pane_index: int, 
                              mapping: Dict[str, Any], desk_dir: Path) -> bool:
        """Update pane directory and title in specific window with task assignment or standby location"""
        try:
            # Check for task assignment first using log files
            agent_id = self._get_agent_id_from_pane_mapping(mapping)
            base_path = desk_dir  # desk_dir is now the base_path directly
            
            # Try to update from task logs (for agents with task assignments)
            task_updated = self._update_pane_from_task_logs(session_name, window_id, pane_index, mapping, base_path)
            
            if task_updated:
                # Agent was moved to task directory via task logs
                logger.debug(f"Agent {agent_id} moved to task directory via task logs")
                return True
            
            # No task assignment - move to standby location
            standby_dir = base_path / "standby"
            standby_dir.mkdir(exist_ok=True)
            
            # Create standby README if it doesn't exist
            readme_file = standby_dir / "README.md"
            if not readme_file.exists():
                with open(readme_file, 'w', encoding='utf-8') as f:
                    f.write("# 待機中エージェント\n\n")
                    f.write("このディレクトリには、現在タスクが割り当てられていないエージェントが配置されています。\n\n")
                    f.write("## エージェント状況\n")
                    f.write("- タスク割り当てありエージェント → `../tasks/` ディレクトリ\n")
                    f.write("- タスク待機中エージェント → このディレクトリ\n\n")
                    f.write("新しいタスクが作成されると、自動的にタスクディレクトリに移動します。\n")
            
            # Move pane to standby directory
            absolute_standby_dir = standby_dir.absolute()
            cmd = ["tmux", "send-keys", "-t", f"{session_name}:{window_id}.{pane_index}", f"cd {absolute_standby_dir}", "Enter"]
            result1 = subprocess.run(cmd, capture_output=True, text=True)
            
            # Set standby pane title
            org_name = mapping.get("title", f"Agent {agent_id}").split(" - ")[0]  # Extract org name
            room_name = mapping.get("title", "").split(" - ")[-1] if " - " in mapping.get("title", "") else "Unknown Room"
            standby_title = f"{org_name} - 待機中 - {room_name}"
            cmd = ["tmux", "select-pane", "-t", f"{session_name}:{window_id}.{pane_index}", "-T", standby_title]
            result2 = subprocess.run(cmd, capture_output=True, text=True)
            
            if result1.returncode == 0 and result2.returncode == 0:
                logger.info(f"📍 Agent {agent_id} placed in standby location: {absolute_standby_dir}")
                return True
            else:
                logger.error(f"Failed to place agent {agent_id} in standby location")
                return False
            
        except Exception as e:
            logger.error(f"Failed to update pane {pane_index} in window {window_id}: {e}")
            return False
    
    def _update_pane_from_task_logs(self, session_name: str, window_id: str, pane_index: int,
                                   mapping: Dict[str, Any], base_path: Path) -> bool:
        """Update pane directory based on task assignment logs"""
        try:
            import json
            from pathlib import Path
            
            # Generate agent ID from pane mapping
            agent_id = self._get_agent_id_from_pane_mapping(mapping)
            logger.debug(f"Checking task logs for agent {agent_id} (pane {window_id}.{pane_index})")
            
            # Look for task assignment logs in tasks directory
            tasks_path = base_path / "tasks"
            if not tasks_path.exists():
                logger.debug(f"No tasks directory found: {tasks_path}")
                return False
            
            # Search through all task directories for agent assignment logs
            assigned_task_dir = None
            task_info = None
            
            for task_dir in tasks_path.iterdir():
                if task_dir.is_dir() and task_dir.name != "main":
                    log_file = task_dir / ".haconiwa" / "agent_assignment.json"
                    if log_file.exists():
                        try:
                            with open(log_file, 'r', encoding='utf-8') as f:
                                assignments = json.load(f)
                                if not isinstance(assignments, list):
                                    assignments = [assignments]
                                
                                # Check if this agent is assigned to this task
                                for assignment in assignments:
                                    if (assignment.get("agent_id") == agent_id and 
                                        assignment.get("space_session") == session_name and
                                        assignment.get("status") == "active"):
                                        
                                        assigned_task_dir = task_dir
                                        task_info = assignment
                                        logger.info(f"Found task assignment: {agent_id} → {task_dir.name}")
                                        break
                                
                                if assigned_task_dir:
                                    break
                                    
                        except Exception as e:
                            logger.warning(f"Could not read assignment log {log_file}: {e}")
            
            # If agent has task assignment, move to task directory
            if assigned_task_dir and task_info:
                return self._move_pane_to_task_directory(session_name, window_id, pane_index, 
                                                       assigned_task_dir, task_info, mapping)
            else:
                logger.debug(f"No active task assignment found for agent {agent_id}")
                return False  # No task assigned - proceed to standby placement
                
        except Exception as e:
            logger.error(f"Error updating pane from task logs: {e}")
            return False
    
    def _move_pane_to_task_directory(self, session_name: str, window_id: str, pane_index: int,
                                   task_dir: Path, task_info: Dict[str, Any], mapping: Dict[str, Any]) -> bool:
        """Move pane to assigned task directory"""
        try:
            agent_id = task_info["agent_id"]
            task_name = task_info["task_name"]
            
            # IMPORTANT: Use absolute path for cd command
            absolute_task_dir = task_dir.absolute()
            
            # Update pane working directory to task directory
            cmd = ["tmux", "send-keys", "-t", f"{session_name}:{window_id}.{pane_index}", 
                   f"cd {absolute_task_dir}", "Enter"]
            result1 = subprocess.run(cmd, capture_output=True, text=True)
            
            # Update pane title to include task info
            original_title = mapping.get("title", f"Desk {mapping['desk_id']}")
            new_title = f"{original_title} [Task: {task_name}]"
            cmd = ["tmux", "select-pane", "-t", f"{session_name}:{window_id}.{pane_index}", "-T", new_title]
            result2 = subprocess.run(cmd, capture_output=True, text=True)
            
            if result1.returncode == 0 and result2.returncode == 0:
                logger.info(f"✅ Moved agent {agent_id} to task directory: {absolute_task_dir}")
                logger.info(f"   📍 Pane: {window_id}.{pane_index}")
                logger.info(f"   📝 Task: {task_name}")
                
                # Update agent assignment log with actual pane information
                self._update_agent_assignment_log_with_pane_info(task_dir, agent_id, session_name, window_id, pane_index)
                
                return True
            else:
                logger.error(f"Failed to move pane {window_id}.{pane_index} to task directory")
                logger.error(f"   send-keys result: {result1.returncode}, select-pane result: {result2.returncode}")
                return False
                
        except Exception as e:
            logger.error(f"Error moving pane to task directory: {e}")
            return False
    
    def _update_agent_assignment_log_with_pane_info(self, task_dir: Path, agent_id: str, session_name: str, window_id: str, pane_index: int) -> bool:
        """Update agent assignment log with actual pane information"""
        try:
            import json
            
            # Path to agent assignment log file
            log_file = task_dir / ".haconiwa" / "agent_assignment.json"
            
            if not log_file.exists():
                logger.warning(f"Agent assignment log file not found: {log_file}")
                return False
            
            # Read current log file
            with open(log_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Ensure data is a list
            if not isinstance(data, list):
                data = [data]
            
            # Find and update the agent assignment
            updated = False
            for assignment in data:
                if (assignment.get("agent_id") == agent_id and 
                    assignment.get("space_session") == session_name and
                    assignment.get("status") == "active"):
                    
                    # Update with actual pane information
                    assignment["tmux_window"] = window_id
                    assignment["tmux_pane"] = int(pane_index)
                    updated = True
                    logger.info(f"📝 Updated log: {agent_id} → window {window_id}, pane {pane_index}")
                    break
            
            if updated:
                # Save updated log
                with open(log_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                logger.info(f"✅ Updated agent assignment log with pane info: {log_file}")
                return True
            else:
                logger.warning(f"Could not find agent assignment for {agent_id} in log file")
                return False
                
        except Exception as e:
            logger.error(f"Error updating agent assignment log with pane info: {e}")
            return False
    
    def _get_room_window_mapping(self, rooms: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
        """Get room to window ID mapping"""
        mapping = {}
        for i, room in enumerate(rooms):
            room_id = room["id"]
            room_name = room["name"]
            mapping[room_id] = {
                "window_id": str(i),
                "name": room_name
            }
        return mapping
    
    def _get_window_id_for_room(self, room_id: str) -> str:
        """Get window ID for specific room"""
        # room-01 → window 0, room-02 → window 1, room-executive → window 2
        if room_id == "room-01":
            return "0"
        elif room_id == "room-02":
            return "1"
        elif room_id == "room-executive":
            return "2"
        else:
            # Extract number from room-XX format
            try:
                room_num = int(room_id.split("-")[1])
                return str(room_num - 1)
            except (IndexError, ValueError):
                return "0"
    
    def _calculate_panes_per_window(self, grid: str, room_count: int) -> Dict[str, Any]:
        """Calculate panes per window based on grid and room count"""
        if grid == "8x4" and room_count == 3:
            # 3 rooms: Alpha (8 panes), Beta (8 panes), Executive (4 panes)
            return {
                "total_panes": 20,
                "panes_per_window": {"room-01": 8, "room-02": 8, "room-executive": 4},
                "layout_per_window": {"room-01": "2x4", "room-02": "2x4", "room-executive": "1x4"}
            }
        elif grid == "8x4" and room_count == 2:
            return {
                "total_panes": 32,
                "panes_per_window": 16,
                "layout_per_window": "4x4"
            }
        else:
            # Default fallback
            return {
                "total_panes": 16,
                "panes_per_window": 16,
                "layout_per_window": "4x4"
            }
    
    def create_room_layout(self, session_name: str, room_config: Dict[str, Any]) -> bool:
        """Create layout for specific room"""
        try:
            room_id = room_config["id"]
            desks = room_config.get("desks", [])
            
            logger.info(f"Creating room layout: {room_id} with {len(desks)} desks")
            
            # This is a simplified implementation
            # In a full implementation, this would handle room-specific layouts
            return True
            
        except Exception as e:
            logger.error(f"Failed to create room layout: {e}")
            return False
    
    def extract_agent_config(self, desk_config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract agent configuration from desk config"""
        agent = desk_config.get("agent", {})
        return {
            "name": agent.get("name", ""),
            "role": agent.get("role", "worker"),
            "model": agent.get("model", "gpt-4o"),
            "env": agent.get("env", {}),
            "desk_id": desk_config["id"]
        }
    
    def update_pane_title(self, session_name: str, pane_index: int, config: Dict[str, Any]) -> bool:
        """Update tmux pane title"""
        title = config.get("title", f"Pane {pane_index}")
        cmd = ["tmux", "select-pane", "-t", f"{session_name}:0.{pane_index}", "-T", title]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode == 0
    
    def create_task_worktree(self, task_config: Dict[str, Any]) -> bool:
        """Create Git worktree for task"""
        try:
            branch = task_config["branch"]
            base_path = task_config["base_path"]
            
            # Create worktree directory
            worktree_path = Path(base_path) / "worktrees" / branch
            
            cmd = ["git", "worktree", "add", str(worktree_path), branch]
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=base_path)
            
            if result.returncode == 0:
                logger.info(f"Created worktree for branch {branch}")
                return True
            else:
                logger.error(f"Failed to create worktree: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to create task worktree: {e}")
            return False
    
    def switch_to_room(self, session_name: str, room_id: str) -> bool:
        """Switch to specific room (tmux window)"""
        try:
            window_id = self._get_window_id_for_room(room_id)
            cmd = ["tmux", "select-window", "-t", f"{session_name}:{window_id}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Switched to {room_id} (window {window_id})")
                return True
            else:
                logger.error(f"Failed to switch to {room_id}: {result.stderr}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to switch to room {room_id}: {e}")
            return False
    
    def calculate_layout(self, grid: str) -> Dict[str, Any]:
        """Calculate layout parameters"""
        if grid == "8x4":
            return {
                "columns": 8,
                "rows": 4,
                "total_panes": 32,
                "panes_per_room": 16
            }
        else:
            # Default fallback
            return {
                "columns": 4,
                "rows": 4,
                "total_panes": 16,
                "panes_per_room": 16
            }
    
    def distribute_organizations(self, organizations: List[Dict[str, Any]], room_count: int) -> List[Dict[str, Any]]:
        """Distribute organizations across rooms"""
        rooms = []
        for i in range(room_count):
            room_id = f"room-{i+1:02d}"
            room_name = ["Alpha Room", "Beta Room"][i] if i < 2 else f"Room {i+1}"
            
            rooms.append({
                "id": room_id,
                "name": room_name,
                "organizations": organizations.copy()  # All orgs in each room
            })
        
        return rooms
    
    def cleanup_session(self, session_name: str, purge_data: bool = False) -> bool:
        """Clean up tmux session and optionally data"""
        try:
            # Kill tmux session
            cmd = ["tmux", "kill-session", "-t", session_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            # Remove from active sessions
            if session_name in self.active_sessions:
                del self.active_sessions[session_name]
            
            logger.info(f"Cleaned up session: {session_name}")
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to cleanup session {session_name}: {e}")
            return False
    
    def attach_to_room(self, session_name: str, room_id: str) -> bool:
        """Attach to specific room in session"""
        try:
            # Switch to room first
            self.switch_to_room(session_name, room_id)
            
            # Attach to session
            cmd = ["tmux", "attach-session", "-t", session_name]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            return result.returncode == 0
            
        except Exception as e:
            logger.error(f"Failed to attach to room {room_id}: {e}")
            return False
    
    def list_spaces(self) -> List[Dict[str, Any]]:
        """List all active spaces from tmux sessions"""
        spaces = []
        
        try:
            # Get actual tmux sessions
            result = subprocess.run(['tmux', 'list-sessions', '-F', '#{session_name}:#{session_windows}'], 
                                   capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.warning("No tmux sessions found or tmux not available")
                return spaces
            
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                
                try:
                    session_name, window_count = line.split(':')
                    
                    # Check if this looks like a haconiwa session
                    if self._is_haconiwa_session(session_name):
                        # Get pane count for this specific session only
                        pane_result = subprocess.run(['tmux', 'list-panes', '-t', session_name, '-a', '-F', '#{session_name}:#{window_index}.#{pane_index}'], 
                                                   capture_output=True, text=True)
                        
                        if pane_result.returncode == 0:
                            # Count panes that belong to this session only
                            panes_for_session = [line for line in pane_result.stdout.strip().split('\n') 
                                               if line.startswith(f"{session_name}:")]
                            pane_count = len(panes_for_session)
                        else:
                            pane_count = 0
                        
                        spaces.append({
                            "name": session_name,
                            "status": "active",
                            "rooms": int(window_count),
                            "panes": pane_count
                        })
                        
                except ValueError:
                    continue
            
            return spaces
            
        except Exception as e:
            logger.error(f"Failed to list spaces: {e}")
            return spaces
    
    def _is_haconiwa_session(self, session_name: str) -> bool:
        """Check if session looks like a haconiwa session"""
        # Simple heuristic: sessions ending with "-company" or having specific patterns
        return (session_name.endswith('-company') or 
                session_name in self.active_sessions or
                any(keyword in session_name.lower() for keyword in ['test', 'multiroom', 'enterprise']))
    
    def start_company(self, company_name: str) -> bool:
        """Start company session"""
        # This is a placeholder - would integrate with existing company logic
        return True
    
    def clone_repository(self, company_name: str) -> bool:
        """Clone repository for company"""
        # This is a placeholder - would integrate with Git operations
        return True

    def _configure_pane_borders(self, session_name: str):
        """Configure pane borders and titles (same as company build)"""
        try:
            # Configure pane borders and titles
            cmd1 = ["tmux", "set-option", "-t", session_name, "pane-border-status", "top"]
            result1 = subprocess.run(cmd1, capture_output=True, text=True)
            
            cmd2 = ["tmux", "set-option", "-t", session_name, "pane-border-format", "#{pane_title}"]
            result2 = subprocess.run(cmd2, capture_output=True, text=True)
            
            if result1.returncode == 0 and result2.returncode == 0:
                logger.info(f"Configured pane borders for session: {session_name}")
            else:
                logger.warning(f"Failed to configure pane borders: {result1.stderr} {result2.stderr}")
        
        except Exception as e:
            logger.error(f"Failed to configure pane borders: {e}")

    def _clone_repository_to_tasks(self, git_config: Dict[str, Any], main_repo_path: Path, force_clone: bool) -> bool:
        """Clone repository to tasks/main/ with improved error handling and user confirmation"""
        try:
            import subprocess
            import shutil
            
            # Create parent directory
            main_repo_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Prepare clone command
            url = git_config["url"]
            auth = git_config.get("auth", "https")
            
            # Check if target directory already exists
            if main_repo_path.exists():
                # Check if it's already a git repository
                git_dir = main_repo_path / ".git"
                if git_dir.exists():
                    logger.info(f"Directory {main_repo_path} is already a git repository, skipping clone")
                    return True
                
                # Check if directory is empty
                if any(main_repo_path.iterdir()):
                    logger.warning(f"⚠️ Directory '{main_repo_path}' already exists and is not empty.")
                    
                    # Show existing contents (first few items)
                    items = list(main_repo_path.iterdir())
                    logger.info("📁 Existing contents:")
                    for i, item in enumerate(items[:5]):  # Show max 5 items
                        item_type = "📁" if item.is_dir() else "📄"
                        logger.info(f"   {item_type} {item.name}")
                    
                    if len(items) > 5:
                        logger.info(f"   ... and {len(items) - 5} more items")
                    
                    # Ask for confirmation unless force flag is set
                    if not force_clone:
                        logger.info("\n🤔 This will replace the existing directory with the Git repository.")
                        
                        # Import typer for confirmation prompt
                        try:
                            import typer
                            continue_anyway = typer.confirm("Do you want to continue and replace the directory?")
                            if not continue_anyway:
                                logger.info("❌ Git clone operation cancelled by user.")
                                logger.info("Continuing without Git repository setup")
                                return True  # Not critical failure, continue without Git
                        except ImportError:
                            # Fallback to input() if typer not available
                            response = input("Do you want to continue and replace the directory? (y/N): ")
                            if response.lower() not in ['y', 'yes']:
                                logger.info("❌ Git clone operation cancelled by user.")
                                logger.info("Continuing without Git repository setup")
                                return True
                    else:
                        logger.info("\n🔨 --force-clone flag is set, replacing directory...")
                    
                    # Remove existing directory
                    shutil.rmtree(main_repo_path)
                    logger.info(f"Removed existing directory: {main_repo_path}")
                else:
                    # Directory exists but is empty, remove it and clone
                    logger.info(f"Empty directory {main_repo_path} exists, removing and cloning")
                    main_repo_path.rmdir()
            
            cmd = ["git", "clone", url, str(main_repo_path)]
            
            # Execute clone
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                logger.info(f"✅ Successfully cloned repository from {url}")
                return True
            else:
                logger.error(f"❌ Failed to clone repository: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("❌ Git clone operation timed out")
            return False
        except Exception as e:
            logger.error(f"❌ Error during git clone: {e}")
            return False
    
    def update_all_panes_from_task_logs(self, session_name: str, space_ref: str) -> int:
        """Update all panes in session based on task assignment logs"""
        try:
            updated_count = 0
            
            if session_name not in self.active_sessions:
                logger.warning(f"Session {session_name} not found in active sessions")
                return 0
            
            session_info = self.active_sessions[session_name]
            desk_mappings = session_info.get("desk_mappings", [])
            desk_distribution = session_info.get("desk_distribution", {})
            
            logger.info(f"🔄 Re-checking task logs for all panes in session: {session_name}")
            
            # Process each room
            for room_id, desks_in_room in desk_distribution.items():
                window_id = self._get_window_id_for_room(room_id)
                
                # Process each pane in the room
                for pane_index, mapping in enumerate(desks_in_room):
                    # Get base path from session info
                    base_path = Path(session_info.get("config", {}).get("base_path", "./"))
                    
                    # Check for task assignment and update if found
                    success = self._update_pane_from_task_logs(session_name, window_id, pane_index, mapping, base_path)
                    if success:
                        # Check if agent was actually moved to task directory
                        agent_id = self._get_agent_id_from_pane_mapping(mapping)
                        if self._check_if_pane_moved_to_task(session_name, window_id, pane_index):
                            updated_count += 1
                            logger.debug(f"Agent {agent_id} successfully updated to task directory")
            
            logger.info(f"🎯 Updated {updated_count} agent panes based on task logs")
            return updated_count
            
        except Exception as e:
            logger.error(f"Failed to update panes from task logs: {e}")
            return 0
    
    def _check_if_pane_moved_to_task(self, session_name: str, window_id: str, pane_index: int) -> bool:
        """Check if pane was successfully moved to task directory"""
        try:
            # Get current path of the pane
            cmd = ["tmux", "list-panes", "-t", f"{session_name}:{window_id}", 
                   "-F", "#{pane_index}:#{pane_current_path}"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    if line.startswith(f"{pane_index}:"):
                        current_path = line.split(':', 1)[1]
                        # Check if path contains 'tasks/' indicating it's in a task directory
                        return "/tasks/" in current_path
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking pane path: {e}")
            return False
    
    def _cleanup_existing_session(self, session_name: str):
        """Clean up existing tmux session"""
        try:
            # Check if session exists first
            check_cmd = ["tmux", "has-session", "-t", session_name]
            check_result = subprocess.run(check_cmd, capture_output=True, text=True)
            
            if check_result.returncode == 0:
                # Session exists, kill it
                kill_cmd = ["tmux", "kill-session", "-t", session_name]
                kill_result = subprocess.run(kill_cmd, capture_output=True, text=True)
                
                if kill_result.returncode == 0:
                    logger.debug(f"Cleaned up existing session: {session_name}")
                else:
                    logger.warning(f"Failed to clean up existing session: {kill_result.stderr}")
            else:
                logger.debug(f"No existing session to clean up: {session_name}")
        
        except Exception as e:
            logger.warning(f"Error during session cleanup: {e}")
    
    def _display_created_structure(self, base_path: Path, organizations: List[Dict[str, Any]]) -> None:
        """Display comprehensive world structure including hierarchy, tasks, and directory mapping"""
        from rich.console import Console
        from rich.tree import Tree
        from rich.panel import Panel
        from rich.table import Table
        from rich.columns import Columns
        
        console = Console()
        
        # Get task assignments for display
        task_assignments = self._get_current_task_assignments()
        
        # Create main world hierarchy tree
        world_tree = self._create_world_hierarchy_tree(base_path, organizations, task_assignments)
        
        # Create directory structure tree
        directory_tree = self._create_directory_structure_tree(base_path, organizations)
        
        # Create task assignment table
        task_table = self._create_task_assignment_table(task_assignments)
        
        # Display all components
        console.print()
        
        # World Hierarchy
        console.print(Panel.fit(
            world_tree,
            title="[bold blue]🌍 World Space Hierarchy[/bold blue]",
            style="blue",
            subtitle="[dim]Logical structure and agent assignments[/dim]"
        ))
        
        # Directory Structure and Task Assignments side by side
        if task_assignments:
            columns = Columns([
                Panel.fit(directory_tree, title="[bold green]📁 Directory Structure[/bold green]", style="green"),
                Panel.fit(task_table, title="[bold yellow]🎯 Task Assignments[/bold yellow]", style="yellow")
            ], equal=True)
            console.print(columns)
        else:
            console.print(Panel.fit(
                directory_tree,
                title="[bold green]📁 Directory Structure[/bold green]",
                style="green"
            ))
        
        console.print()
    
    def _create_world_hierarchy_tree(self, base_path: Path, organizations: List[Dict[str, Any]], task_assignments: Dict[str, Any]):
        """Create world hierarchy tree showing logical space structure"""
        from rich.tree import Tree
        
        tree = Tree(f"🌍 [bold cyan]World: {base_path.name}[/bold cyan]")
        
        # Nation level
        nation_branch = tree.add("🏴 [blue]Nation: Japan[/blue]")
        
        # City level  
        city_branch = nation_branch.add("🏙️ [blue]City: Tokyo[/blue]")
        
        # Village level
        village_branch = city_branch.add("🏘️ [blue]Village: Harmony Village[/blue]")
        
        # Company level
        company_branch = village_branch.add("🏢 [green]Company: Synergy Development[/green]")
        
        # Building level
        building_branch = company_branch.add("🏢 [yellow]Building: Headquarters[/yellow]")
        
        # Floor 1 - Engineering Floor
        floor1_branch = building_branch.add("🏠 [yellow]Floor 1 - Engineering Floor[/yellow]")
        
        # Room level on Floor 1
        alpha_room = floor1_branch.add("🚪 [cyan]Alpha Room (room-01)[/cyan]")
        beta_room = floor1_branch.add("🚪 [cyan]Beta Room (room-02)[/cyan]")
        
        # Floor 2 - Executive Floor
        floor2_branch = building_branch.add("🏠 [gold1]Floor 2 - Executive Floor[/gold1]")
        
        # Executive Room on Floor 2
        executive_room = floor2_branch.add("🚪 [gold1]Executive Room (room-executive)[/gold1]")
        
        # Get organization data from Organization CRD for detailed role mapping
        organization_crd_data = self._get_organization_crd_for_display()
        
        # Add organizations and desks to each room with actual role information
        for i, org in enumerate(organizations[:4]):  # First 4 organizations for Alpha/Beta
            org_id = i + 1
            org_name = org.get("name", f"Organization {org_id}")
            department_id = org.get("department_id", "unknown")
            
            # Get actual roles for this department from Organization CRD
            dept_roles = self._get_department_roles(organization_crd_data, department_id)
            
            # Only show first 2 orgs in Alpha, next 2 orgs in Beta
            if i < 2:  # Organizations 1-2 in Alpha Room
                alpha_org = alpha_room.add(f"📋 [magenta]{org_name}[/magenta]")
                for j in range(4):  # 4 panes per organization per room
                    if j == 0:
                        role_part = "pm"
                        role_title = dept_roles.get("lead", "Team Lead") if dept_roles else "PM"
                    else:
                        role_part = f"wk-{chr(ord('a')+j-1)}"
                        role_titles = dept_roles.get("workers", ["Senior Dev", "Dev", "Junior Dev"]) if dept_roles else ["Senior Dev", "Dev", "Junior Dev"]
                        role_title = role_titles[j-1] if j-1 < len(role_titles) else f"Worker {chr(ord('A')+j-1)}"
                        
                    desk_id = f"org{org_id:02d}-{role_part}-r1"
                    task_info = task_assignments.get(desk_id, {})
                    task_display = f" → [green]{task_info['task_name']}[/green]" if task_info else " [dim](standby)[/dim]"
                    alpha_org.add(f"👤 [white]{role_title}[/white] ({desk_id}){task_display}")
                    
            else:  # Organizations 3-4 in Beta Room
                beta_org = beta_room.add(f"📋 [magenta]{org_name}[/magenta]")
                for j in range(4):  # 4 panes per organization per room
                    if j == 0:
                        role_part = "pm"
                        role_title = dept_roles.get("lead", "Team Lead") if dept_roles else "PM"
                    else:
                        role_part = f"wk-{chr(ord('a')+j-1)}"
                        role_titles = dept_roles.get("workers", ["Senior Dev", "Dev", "Junior Dev"]) if dept_roles else ["Senior Dev", "Dev", "Junior Dev"]
                        role_title = role_titles[j-1] if j-1 < len(role_titles) else f"Worker {chr(ord('A')+j-1)}"
                        
                    desk_id = f"org{org_id:02d}-{role_part}-r2"
                    task_info = task_assignments.get(desk_id, {})
                    task_display = f" → [green]{task_info['task_name']}[/green]" if task_info else " [dim](standby)[/dim]"
                    beta_org.add(f"👤 [white]{role_title}[/white] ({desk_id}){task_display}")
        
        # Executive Room - Organization 5 on Floor 2
        if len(organizations) >= 5:
            exec_org = organizations[4]  # 5th organization (Executive)
            exec_org_name = exec_org.get("name", "Executive Leadership")
            
            # Get executive roles from Organization CRD
            exec_dept_roles = self._get_department_roles(organization_crd_data, "executive")
            
            exec_branch = executive_room.add(f"📋 [gold1]{exec_org_name}[/gold1]")
            
            # CEO, CTO, COO, Assistant
            exec_roles = ["ceo", "cto", "coo", "assistant"]
            exec_titles = ["CEO", "CTO", "COO", "Executive Assistant"]
            
            # Use actual titles from Organization CRD if available
            if exec_dept_roles:
                actual_exec_titles = []
                for role in exec_dept_roles.get("workers", []):
                    if "ceo" in role.lower():
                        actual_exec_titles.append(role)
                    elif "cto" in role.lower():
                        actual_exec_titles.append(role)
                    elif "coo" in role.lower():
                        actual_exec_titles.append(role)
                
                # Add missing titles
                if len(actual_exec_titles) < 3:
                    actual_exec_titles.extend(["CEO", "CTO", "COO"][len(actual_exec_titles):])
                actual_exec_titles.append("Executive Assistant")
                exec_titles = actual_exec_titles[:4]
            
            for i, (role_name, role_title) in enumerate(zip(exec_roles, exec_titles)):
                desk_id = f"org05-{role_name}-re"
                task_info = task_assignments.get(desk_id, {})
                task_display = f" → [green]{task_info['task_name']}[/green]" if task_info else " [dim](standby)[/dim]"
                exec_branch.add(f"👤 [white]{role_title}[/white] ({desk_id}){task_display}")
        
        return tree
    
    def _create_directory_structure_tree(self, base_path: Path, organizations: List[Dict[str, Any]]):
        """Create directory structure tree"""
        from rich.tree import Tree
        
        tree = Tree(f"📁 [bold cyan]{base_path.name}/[/bold cyan]")
        
        # Tasks directory
        tasks_branch = tree.add("📁 [yellow]tasks/[/yellow] (Git Repository & Worktrees)")
        tasks_branch.add("📁 [green]main/[/green] (Main Repository)")
        
        # Check for actual task directories and show them
        tasks_path = base_path / "tasks"
        task_count = 0
        if tasks_path.exists():
            task_dirs = [d for d in tasks_path.iterdir() if d.is_dir() and d.name != "main"]
            if task_dirs:
                for task_dir in sorted(task_dirs):
                    # Try to get task description from assignment log
                    task_display = task_dir.name
                    assignment_log = task_dir / ".haconiwa" / "agent_assignment.json"
                    if assignment_log.exists():
                        try:
                            import json
                            with open(assignment_log, 'r', encoding='utf-8') as f:
                                log_data = json.load(f)
                                if not isinstance(log_data, list):
                                    log_data = [log_data]
                                if log_data and log_data[0].get("agent_id"):
                                    agent_id = log_data[0]["agent_id"]
                                    task_display = f"{task_dir.name} → {agent_id}"
                        except:
                            pass
                    
                    tasks_branch.add(f"📁 [cyan]{task_display}[/cyan] (Task Worktree)")
                    task_count += 1
        
        # Show standby directory (created automatically)
        standby_branch = tree.add("📁 [dim]standby/[/dim] (Unassigned Agents)")
        
        # Add summary info
        if task_count > 0:
            tree.add(f"[dim]📊 Active Tasks: {task_count} | Tmux Panes: 32 (16 per room)[/dim]")
        else:
            tree.add(f"[dim]📊 No active tasks | Tmux Panes: 32 (16 per room)[/dim]")
        
        return tree
    
    def _create_task_assignment_table(self, task_assignments: Dict[str, Any]):
        """Create task assignment table"""
        from rich.table import Table
        
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Task", style="green", width=40)
        table.add_column("Room", style="blue", width=16)
        table.add_column("Role", style="magenta", width=20)
        table.add_column("Agent", style="yellow", width=20)
        
        if not task_assignments:
            table.add_row("[dim]No task assignments[/dim]", "", "", "")
            return table
        
        # Get organization data from Organization CRD for role information
        organization_crd_data = self._get_organization_crd_for_display()
        organizations = self._get_organization_data("synergy-development-org")
        
        # Add assignments for first 4 organizations (Alpha and Beta rooms)
        for i, org in enumerate(organizations[:4]):
            org_id = i + 1
            org_name = org.get("name", f"Organization {org_id}")
            department_id = org.get("department_id", "unknown")
            
            # Get actual roles for this department from Organization CRD
            dept_roles = self._get_department_roles(organization_crd_data, department_id)
            
            # Room assignment based on organization ID
            room_name = "Alpha Room" if i < 2 else "Beta Room"
            room_id = "room-01" if i < 2 else "room-02"
            
            for j in range(4):  # 4 roles per organization
                if j == 0:
                    role_part = "pm"
                    role_title = dept_roles.get("lead", "Team Lead") if dept_roles else "Project Manager"
                else:
                    role_part = f"wk-{chr(ord('a')+j-1)}"
                    role_titles = dept_roles.get("workers", ["Senior Developer", "Developer", "Junior Developer"]) if dept_roles else ["Senior Developer", "Developer", "Junior Developer"]
                    role_title = role_titles[j-1] if j-1 < len(role_titles) else f"Worker {chr(ord('A')+j-1)}"
                
                agent_id = f"org{org_id:02d}-{role_part}-{'r1' if i < 2 else 'r2'}"
                
                # Check for task assignment using the exact agent_id
                assigned_task = ""
                for task_agent_id, task_info in task_assignments.items():
                    if task_agent_id == agent_id:
                        assigned_task = task_info.get("task_name", "Unknown Task")
                        break
                
                if not assigned_task:
                    assigned_task = "[dim]standby[/dim]"
                
                table.add_row(assigned_task, room_name, role_title, agent_id)
        
        # Add Executive Leadership assignments (Organization 5)
        if len(organizations) >= 5:
            exec_org = organizations[4]  # 5th organization
            exec_org_name = exec_org.get("name", "Executive Leadership")
            
            # Get executive roles from Organization CRD
            exec_dept_roles = self._get_department_roles(organization_crd_data, "executive")
            
            # Executive roles
            exec_roles = ["ceo", "cto", "coo", "assistant"]
            exec_titles = ["CEO", "CTO", "COO", "Executive Assistant"]
            
            # Use actual titles from Organization CRD if available
            if exec_dept_roles:
                actual_exec_titles = []
                exec_role_data = exec_dept_roles.get("workers", [])
                for role_name in exec_role_data:
                    if "ceo" in role_name.lower():
                        actual_exec_titles.append(role_name)
                    elif "cto" in role_name.lower():
                        actual_exec_titles.append(role_name)
                    elif "coo" in role_name.lower():
                        actual_exec_titles.append(role_name)
                
                # Fill in missing standard titles
                if len(actual_exec_titles) < 3:
                    standard_titles = ["CEO", "CTO", "COO"]
                    for title in standard_titles:
                        if not any(title.lower() in t.lower() for t in actual_exec_titles):
                            actual_exec_titles.append(title)
                            if len(actual_exec_titles) >= 3:
                                break
                                
                actual_exec_titles.append("Executive Assistant")
                exec_titles = actual_exec_titles[:4]
            
            for i, (role_name, role_title) in enumerate(zip(exec_roles, exec_titles)):
                agent_id = f"org05-{role_name}-re"
                
                # Check for task assignment using the exact agent_id
                assigned_task = ""
                for task_agent_id, task_info in task_assignments.items():
                    if task_agent_id == agent_id:
                        assigned_task = task_info.get("task_name", "Unknown Task")
                        break
                
                if not assigned_task:
                    assigned_task = "[dim]standby[/dim]"
                
                table.add_row(assigned_task, "Executive Room", role_title, agent_id)
        
        return table
    
    def _get_current_task_assignments(self) -> Dict[str, Dict[str, Any]]:
        """Get current task assignments for display by reading from task directories"""
        assignments = {}
        
        # First check stored task assignments
        if hasattr(self, 'task_assignments') and self.task_assignments:
            for agent_id, task_info in self.task_assignments.items():
                # Extract room from agent ID (org01-pm-r1 → r1)
                room = agent_id.split("-")[-1] if "-" in agent_id else "r1"
                assignments[agent_id] = {
                    "task_name": task_info.get("name", "Unknown Task"),
                    "room": room,
                    "status": "active"
                }
        
        # Also check task directories for additional assignment info
        for session_name, session_info in self.active_sessions.items():
            config = session_info.get("config", {})
            base_path = Path(config.get("base_path", "./"))
            tasks_path = base_path / "tasks"
            
            if tasks_path.exists():
                # Scan task directories for assignment logs
                for task_dir in tasks_path.iterdir():
                    if task_dir.is_dir() and task_dir.name != "main":
                        assignment_log = task_dir / ".haconiwa" / "agent_assignment.json"
                        if assignment_log.exists():
                            try:
                                import json
                                with open(assignment_log, 'r', encoding='utf-8') as f:
                                    log_data = json.load(f)
                                    
                                # Handle both single assignment and list format
                                if not isinstance(log_data, list):
                                    log_data = [log_data]
                                
                                for assignment in log_data:
                                    agent_id = assignment.get("agent_id")
                                    if agent_id and assignment.get("status") == "active":
                                        room = agent_id.split("-")[-1] if "-" in agent_id else "r1"
                                        assignments[agent_id] = {
                                            "task_name": assignment.get("task_name", task_dir.name),
                                            "room": room,
                                            "status": "active"
                                        }
                                        
                            except Exception as e:
                                logger.debug(f"Could not read assignment log {assignment_log}: {e}")
        
        return assignments
    
    def _get_organization_crd_for_display(self) -> Optional[Dict[str, Any]]:
        """Get Organization CRD data for display purposes"""
        try:
            # Try to get Organization CRD from applied resources
            import sys
            if hasattr(sys.modules.get('__main__'), '_current_applier'):
                applier = getattr(sys.modules['__main__'], '_current_applier')
                applied_resources = applier.get_applied_resources()
                
                # Find Organization CRD
                for resource_key, resource in applied_resources.items():
                    if resource_key.startswith("Organization/"):
                        logger.debug(f"Found Organization CRD for display: {resource.metadata.name}")
                        return resource
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not get Organization CRD for display: {e}")
            return None
    
    def _get_department_roles(self, organization_crd, department_id: str) -> Optional[Dict[str, Any]]:
        """Get roles for specific department from Organization CRD"""
        try:
            if not organization_crd:
                return None
            
            # Find the department
            for dept in organization_crd.spec.hierarchy.departments:
                if dept.id == department_id:
                    roles = dept.roles
                    logger.debug(f"Found {len(roles)} roles for department {department_id}")
                    
                    # Extract lead and worker roles
                    lead_role = None
                    worker_roles = []
                    
                    for role in roles:
                        role_type = getattr(role, 'roleType', '')
                        title = getattr(role, 'title', '')
                        
                        # Identify lead roles (management type or specific titles)
                        if (role_type == 'management' or 
                            'lead' in title.lower() or 
                            'manager' in title.lower() or
                            'head' in title.lower()):
                            lead_role = title
                        else:
                            worker_roles.append(title)
                    
                    # Ensure we have at least 3 worker roles for 32-pane structure
                    while len(worker_roles) < 3:
                        worker_roles.append(f"Worker {len(worker_roles) + 1}")
                    
                    return {
                        "lead": lead_role or "Team Lead",
                        "workers": worker_roles[:3]  # Take first 3 for consistency
                    }
            
            return None
            
        except Exception as e:
            logger.warning(f"Could not get roles for department {department_id}: {e}")
            return None
 