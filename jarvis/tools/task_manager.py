from jarvis.tool_registry import ToolDef
import json
import os
from datetime import datetime
from typing import Dict, List, Optional

TASKS_FILE = "jarvis_tasks.json"

def _load_tasks() -> Dict:
    if os.path.exists(TASKS_FILE):
        try:
            with open(TASKS_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {"projects": {}, "next_id": 1}
    return {"projects": {}, "next_id": 1}

def _save_tasks(data: Dict) -> None:
    with open(TASKS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def create_project(name: str, description: str, goal: str) -> str:
    try:
        data = _load_tasks()
        project_id = f"proj_{data['next_id']}"
        data['next_id'] += 1
        data['projects'][project_id] = {
            "id": project_id,
            "name": name,
            "description": description,
            "goal": goal,
            "status": "active",
            "created_at": datetime.now().isoformat(),
            "tasks": [],
            "next_task_id": 1
        }
        _save_tasks(data)
        return f"Project '{name}' created with ID: {project_id}"
    except Exception as e:
        return f"Error creating project: {str(e)}"

def add_task(project_id: str, title: str, description: str, estimated_hours: float = 1.0, dependencies: str = "") -> str:
    try:
        data = _load_tasks()
        if project_id not in data['projects']:
            return f"Project {project_id} not found"
        project = data['projects'][project_id]
        task_id = f"task_{project['next_task_id']}"
        project['next_task_id'] += 1
        deps = [d.strip() for d in dependencies.split(',') if d.strip()]
        task = {
            "id": task_id,
            "title": title,
            "description": description,
            "status": "pending",
            "estimated_hours": estimated_hours,
            "actual_hours": 0.0,
            "dependencies": deps,
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "notes": []
        }
        project['tasks'].append(task)
        _save_tasks(data)
        return f"Task '{title}' added to {project_id} with ID: {task_id}"
    except Exception as e:
        return f"Error adding task: {str(e)}"

def update_task_status(project_id: str, task_id: str, status: str, actual_hours: float = 0.0, note: str = "") -> str:
    try:
        data = _load_tasks()
        if project_id not in data['projects']:
            return f"Project {project_id} not found"
        project = data['projects'][project_id]
        task = None
        for t in project['tasks']:
            if t['id'] == task_id:
                task = t
                break
        if not task:
            return f"Task {task_id} not found in {project_id}"
        valid_statuses = ['pending', 'in_progress', 'completed', 'blocked']
        if status not in valid_statuses:
            return f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        task['status'] = status
        if actual_hours > 0:
            task['actual_hours'] = actual_hours
        if status == 'completed':
            task['completed_at'] = datetime.now().isoformat()
        if note:
            task['notes'].append({"timestamp": datetime.now().isoformat(), "content": note})
        _save_tasks(data)
        return f"Task {task_id} status updated to: {status}"
    except Exception as e:
        return f"Error updating task: {str(e)}"

def get_next_tasks(project_id: str, limit: int = 5) -> str:
    try:
        data = _load_tasks()
        if project_id not in data['projects']:
            return f"Project {project_id} not found"
        project = data['projects'][project_id]
        completed_tasks = {t['id'] for t in project['tasks'] if t['status'] == 'completed'}
        actionable = []
        for task in project['tasks']:
            if task['status'] in ['pending', 'in_progress']:
                deps_met = all(dep in completed_tasks for dep in task['dependencies'])
                if deps_met:
                    actionable.append({"id": task['id'], "title": task['title'], "status": task['status'], "estimated_hours": task['estimated_hours'], "description": task['description']})
        actionable = actionable[:limit]
        if not actionable:
            return "No actionable tasks found. Check dependencies or all tasks may be complete."
        return json.dumps(actionable, indent=2)
    except Exception as e:
        return f"Error getting next tasks: {str(e)}"

def get_project_status(project_id: str) -> str:
    try:
        data = _load_tasks()
        if project_id not in data['projects']:
            return f"Project {project_id} not found"
        project = data['projects'][project_id]
        tasks = project['tasks']
        total = len(tasks)
        completed = sum(1 for t in tasks if t['status'] == 'completed')
        in_progress = sum(1 for t in tasks if t['status'] == 'in_progress')
        blocked = sum(1 for t in tasks if t['status'] == 'blocked')
        pending = sum(1 for t in tasks if t['status'] == 'pending')
        estimated_total = sum(t['estimated_hours'] for t in tasks)
        actual_total = sum(t['actual_hours'] for t in tasks)
        progress = (completed / total * 100) if total > 0 else 0
        status = {"project": {"id": project_id, "name": project['name'], "goal": project['goal'], "status": project['status']}, "tasks": {"total": total, "completed": completed, "in_progress": in_progress, "blocked": blocked, "pending": pending, "progress_percent": round(progress, 1)}, "effort": {"estimated_hours": estimated_total, "actual_hours": actual_total, "efficiency_percent": round((estimated_total / actual_total * 100) if actual_total > 0 else 100, 1)}}
        return json.dumps(status, indent=2)
    except Exception as e:
        return f"Error getting project status: {str(e)}"

def list_projects(status_filter: str = "all") -> str:
    try:
        data = _load_tasks()
        projects = []
        for proj_id, proj in data['projects'].items():
            if status_filter == "all" or proj['status'] == status_filter:
                tasks = proj['tasks']
                completed = sum(1 for t in tasks if t['status'] == 'completed')
                total = len(tasks)
                projects.append({"id": proj_id, "name": proj['name'], "status": proj['status'], "goal": proj['goal'], "progress": f"{completed}/{total} tasks"})
        if not projects:
            return "No projects found"
        return json.dumps(projects, indent=2)
    except Exception as e:
        return f"Error listing projects: {str(e)}"

def register(registry):
    registry.register(ToolDef(name="create_project", description="Create a new project with a goal. Returns project ID to use in other task commands.", parameters={"properties": {"name": {"type": "string", "description": "Project name"}, "description": {"type": "string", "description": "Project description"}, "goal": {"type": "string", "description": "Main goal/objective"}}, "required": ["name", "description", "goal"]}, func=create_project))
    registry.register(ToolDef(name="add_task", description="Add a task to a project. Can specify dependencies on other task IDs (comma-separated).", parameters={"properties": {"project_id": {"type": "string", "description": "Project ID (e.g., proj_1)"}, "title": {"type": "string", "description": "Task title"}, "description": {"type": "string", "description": "Task description"}, "estimated_hours": {"type": "number", "description": "Estimated hours", "default": 1.0}, "dependencies": {"type": "string", "description": "Comma-separated task IDs this depends on", "default": ""}}, "required": ["project_id", "title", "description"]}, func=add_task))
    registry.register(ToolDef(name="update_task_status", description="Update task status: pending, in_progress, completed, or blocked. Can add actual hours and notes.", parameters={"properties": {"project_id": {"type": "string", "description": "Project ID"}, "task_id": {"type": "string", "description": "Task ID (e.g., task_1)"}, "status": {"type": "string", "description": "New status: pending, in_progress, completed, blocked"}, "actual_hours": {"type": "number", "description": "Actual hours spent", "default": 0.0}, "note": {"type": "string", "description": "Optional note about the update", "default": ""}}, "required": ["project_id", "task_id", "status"]}, func=update_task_status))
    registry.register(ToolDef(name="get_next_tasks", description="Get the next actionable tasks based on dependencies. Returns tasks whose dependencies are met.", parameters={"properties": {"project_id": {"type": "string", "description": "Project ID"}, "limit": {"type": "integer", "description": "Max tasks to return", "default": 5}}, "required": ["project_id"]}, func=get_next_tasks))
    registry.register(ToolDef(name="get_project_status", description="Get comprehensive project status with progress metrics, task counts, and effort tracking.", parameters={"properties": {"project_id": {"type": "string", "description": "Project ID"}}, "required": ["project_id"]}, func=get_project_status))
    registry.register(ToolDef(name="list_projects", description="List all projects with optional status filter (active, completed, archived).", parameters={"properties": {"status_filter": {"type": "string", "description": "Filter by status: all, active, completed, archived", "default": "all"}}, "required": []}, func=list_projects))