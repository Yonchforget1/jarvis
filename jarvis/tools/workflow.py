from jarvis.tool_registry import ToolDef
import json
from typing import Dict, List, Any, Optional
from enum import Enum
import time

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class WorkflowEngine:
    def __init__(self):
        self.workflows: Dict[str, Dict] = {}
        self.executions: Dict[str, Dict] = {}
    
    def create_workflow(self, workflow_id: str, steps: List[Dict]) -> Dict:
        if workflow_id in self.workflows:
            return {"error": f"Workflow {workflow_id} already exists"}
        
        for step in steps:
            if "id" not in step or "action" not in step:
                return {"error": "Each step must have 'id' and 'action' fields"}
        
        self.workflows[workflow_id] = {
            "id": workflow_id,
            "steps": steps,
            "created_at": time.time()
        }
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "step_count": len(steps)
        }
    
    def execute_workflow(self, workflow_id: str, context: Optional[Dict] = None) -> Dict:
        if workflow_id not in self.workflows:
            return {"error": f"Workflow {workflow_id} not found"}
        
        workflow = self.workflows[workflow_id]
        execution_id = f"{workflow_id}_{int(time.time() * 1000)}"
        
        execution = {
            "id": execution_id,
            "workflow_id": workflow_id,
            "status": "running",
            "context": context or {},
            "steps": [],
            "started_at": time.time(),
            "completed_at": None
        }
        
        self.executions[execution_id] = execution
        
        for step_def in workflow["steps"]:
            step_result = self._execute_step(step_def, execution["context"])
            
            execution["steps"].append({
                "id": step_def["id"],
                "status": step_result["status"],
                "output": step_result.get("output"),
                "error": step_result.get("error")
            })
            
            if step_result["status"] == "failed":
                if not step_def.get("continue_on_failure", False):
                    execution["status"] = "failed"
                    execution["completed_at"] = time.time()
                    return self._format_execution_result(execution)
            
            if "output" in step_result:
                execution["context"][step_def["id"]] = step_result["output"]
        
        execution["status"] = "completed"
        execution["completed_at"] = time.time()
        
        return self._format_execution_result(execution)
    
    def _execute_step(self, step_def: Dict, context: Dict) -> Dict:
        try:
            dependencies = step_def.get("depends_on", [])
            for dep in dependencies:
                if dep not in context:
                    return {
                        "status": "failed",
                        "error": f"Dependency {dep} not satisfied"
                    }
            
            action = step_def["action"]
            params = step_def.get("parameters", {})
            
            resolved_params = self._resolve_params(params, context)
            
            output = {
                "action": action,
                "params": resolved_params,
                "executed": True
            }
            
            return {
                "status": "completed",
                "output": output
            }
            
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e)
            }
    
    def _resolve_params(self, params: Dict, context: Dict) -> Dict:
        resolved = {}
        for key, value in params.items():
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                ref = value[2:-1]
                parts = ref.split(".")
                resolved_value = context
                for part in parts:
                    if isinstance(resolved_value, dict):
                        resolved_value = resolved_value.get(part)
                    else:
                        resolved_value = None
                        break
                resolved[key] = resolved_value if resolved_value is not None else value
            else:
                resolved[key] = value
        return resolved
    
    def _format_execution_result(self, execution: Dict) -> Dict:
        duration = None
        if execution["completed_at"]:
            duration = execution["completed_at"] - execution["started_at"]
        
        return {
            "execution_id": execution["id"],
            "workflow_id": execution["workflow_id"],
            "status": execution["status"],
            "steps_completed": len([s for s in execution["steps"] if s["status"] == "completed"]),
            "steps_failed": len([s for s in execution["steps"] if s["status"] == "failed"]),
            "duration_seconds": round(duration, 2) if duration else None,
            "steps": execution["steps"],
            "final_context": execution["context"]
        }
    
    def get_execution_status(self, execution_id: str) -> Dict:
        if execution_id not in self.executions:
            return {"error": f"Execution {execution_id} not found"}
        
        return self._format_execution_result(self.executions[execution_id])
    
    def list_workflows(self) -> Dict:
        return {
            "workflows": [
                {
                    "id": wf["id"],
                    "step_count": len(wf["steps"]),
                    "created_at": wf["created_at"]
                }
                for wf in self.workflows.values()
            ]
        }

_engine = WorkflowEngine()

def create_workflow(workflow_id: str, steps: str) -> str:
    try:
        steps_list = json.loads(steps)
        result = _engine.create_workflow(workflow_id, steps_list)
        return json.dumps(result, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def execute_workflow(workflow_id: str, context: str = "{}") -> str:
    try:
        context_dict = json.loads(context)
        result = _engine.execute_workflow(workflow_id, context_dict)
        return json.dumps(result, indent=2)
    except json.JSONDecodeError as e:
        return json.dumps({"error": f"Invalid JSON: {str(e)}"})
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_workflow_status(execution_id: str) -> str:
    try:
        result = _engine.get_execution_status(execution_id)
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

def list_workflows() -> str:
    try:
        result = _engine.list_workflows()
        return json.dumps(result, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})

def register(registry):
    registry.register(ToolDef(
        name="create_workflow",
        description="Create a new multi-step workflow with dependencies and error handling. Steps execute sequentially and can reference outputs from previous steps.",
        parameters={
            "properties": {
                "workflow_id": {"type": "string", "description": "Unique identifier for the workflow"},
                "steps": {"type": "string", "description": "JSON array of step objects, each with: id, action, parameters (optional), depends_on (optional), continue_on_failure (optional)"}
            },
            "required": ["workflow_id", "steps"]
        },
        func=create_workflow
    ))
    
    registry.register(ToolDef(
        name="execute_workflow",
        description="Execute a registered workflow with optional context variables. Returns execution ID and results for each step.",
        parameters={
            "properties": {
                "workflow_id": {"type": "string", "description": "ID of the workflow to execute"},
                "context": {"type": "string", "description": "JSON object with initial context/variables", "default": "{}"}
            },
            "required": ["workflow_id"]
        },
        func=execute_workflow
    ))
    
    registry.register(ToolDef(
        name="get_workflow_status",
        description="Get detailed status of a workflow execution including step results and duration.",
        parameters={
            "properties": {
                "execution_id": {"type": "string", "description": "Execution ID returned from execute_workflow"}
            },
            "required": ["execution_id"]
        },
        func=get_workflow_status
    ))
    
    registry.register(ToolDef(
        name="list_workflows",
        description="List all registered workflows with their metadata.",
        parameters={"properties": {}, "required": []},
        func=list_workflows
    ))