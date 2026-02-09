from jarvis.tool_registry import ToolDef
import ast
import os
import json
from pathlib import Path
from typing import Dict, List, Any

def analyze_code_file(filepath: str) -> str:
    """Analyze a Python file for code quality issues.
    
    Args:
        filepath: Path to Python file to analyze
    
    Returns:
        JSON report with issues, metrics, and suggestions
    """
    try:
        path = Path(filepath)
        if not path.exists():
            return json.dumps({"error": f"File not found: {filepath}"})
        
        if not filepath.endswith(".py"):
            return json.dumps({"error": "Only Python files (.py) are supported"})
        
        with open(path, "r", encoding="utf-8") as f:
            code = f.read()
        
        issues = []
        metrics = {"lines": 0, "functions": 0, "classes": 0, "imports": 0}
        suggestions = []
        
        # Parse AST
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            return json.dumps({
                "error": f"Syntax error: {e}",
                "line": e.lineno,
                "offset": e.offset
            })
        
        # Count lines
        metrics["lines"] = len(code.splitlines())
        
        # Analyze AST nodes
        for node in ast.walk(tree):
            # Count functions
            if isinstance(node, ast.FunctionDef):
                metrics["functions"] += 1
                
                # Check function length
                if hasattr(node, "lineno") and hasattr(node, "end_lineno"):
                    func_lines = node.end_lineno - node.lineno
                    if func_lines > 50:
                        issues.append({
                            "type": "long_function",
                            "line": node.lineno,
                            "name": node.name,
                            "length": func_lines,
                            "severity": "warning"
                        })
                        suggestions.append(f"Function '{node.name}' is {func_lines} lines - consider breaking it into smaller functions")
                
                # Check missing docstrings
                if not ast.get_docstring(node):
                    issues.append({
                        "type": "missing_docstring",
                        "line": node.lineno,
                        "name": node.name,
                        "severity": "info"
                    })
                
                # Check parameter count
                if len(node.args.args) > 5:
                    issues.append({
                        "type": "too_many_parameters",
                        "line": node.lineno,
                        "name": node.name,
                        "count": len(node.args.args),
                        "severity": "warning"
                    })
                    suggestions.append(f"Function '{node.name}' has {len(node.args.args)} parameters - consider using a config object")
            
            # Count classes
            elif isinstance(node, ast.ClassDef):
                metrics["classes"] += 1
                
                # Check missing class docstrings
                if not ast.get_docstring(node):
                    issues.append({
                        "type": "missing_docstring",
                        "line": node.lineno,
                        "name": node.name,
                        "severity": "info"
                    })
            
            # Count imports
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                metrics["imports"] += 1
            
            # Check nested complexity
            elif isinstance(node, (ast.For, ast.While, ast.If)):
                depth = _get_nesting_depth(node)
                if depth > 3:
                    issues.append({
                        "type": "deep_nesting",
                        "line": getattr(node, "lineno", 0),
                        "depth": depth,
                        "severity": "warning"
                    })
                    suggestions.append(f"Deep nesting (level {depth}) at line {getattr(node, 'lineno', 0)} - consider extracting to functions")
            
            # Check bare except
            elif isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    issues.append({
                        "type": "bare_except",
                        "line": node.lineno,
                        "severity": "error"
                    })
                    suggestions.append(f"Bare except clause at line {node.lineno} - specify exception types")
        
        # Calculate complexity score (lower is better)
        complexity = len(issues) + (metrics["lines"] // 100)
        
        # Generate overall quality score (0-100, higher is better)
        quality_score = max(0, 100 - (len([i for i in issues if i["severity"] == "error"]) * 10) - (len([i for i in issues if i["severity"] == "warning"]) * 3))
        
        return json.dumps({
            "file": str(path),
            "metrics": metrics,
            "issues": issues,
            "issue_count": len(issues),
            "suggestions": suggestions,
            "complexity": complexity,
            "quality_score": quality_score
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

def _get_nesting_depth(node: ast.AST, depth: int = 1) -> int:
    """Calculate maximum nesting depth of control structures."""
    max_depth = depth
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.For, ast.While, ast.If, ast.With)):
            child_depth = _get_nesting_depth(child, depth + 1)
            max_depth = max(max_depth, child_depth)
    return max_depth

def analyze_directory(dirpath: str, recursive: bool = True) -> str:
    """Analyze all Python files in a directory.
    
    Args:
        dirpath: Path to directory to analyze
        recursive: Whether to analyze subdirectories
    
    Returns:
        JSON summary report of all files
    """
    try:
        path = Path(dirpath)
        if not path.exists():
            return json.dumps({"error": f"Directory not found: {dirpath}"})
        
        if not path.is_dir():
            return json.dumps({"error": f"Not a directory: {dirpath}"})
        
        pattern = "**/*.py" if recursive else "*.py"
        py_files = list(path.glob(pattern))
        
        if not py_files:
            return json.dumps({"message": "No Python files found", "files": []})
        
        results = []
        total_issues = 0
        total_lines = 0
        
        for pyfile in py_files:
            # Skip __pycache__ and similar
            if "__pycache__" in str(pyfile):
                continue
            
            analysis = analyze_code_file(str(pyfile))
            data = json.loads(analysis)
            
            if "error" not in data:
                results.append({
                    "file": str(pyfile.relative_to(path)),
                    "issues": data.get("issue_count", 0),
                    "quality_score": data.get("quality_score", 0),
                    "lines": data.get("metrics", {}).get("lines", 0)
                })
                total_issues += data.get("issue_count", 0)
                total_lines += data.get("metrics", {}).get("lines", 0)
        
        # Sort by quality score (worst first)
        results.sort(key=lambda x: x["quality_score"])
        
        avg_quality = sum(r["quality_score"] for r in results) / len(results) if results else 0
        
        return json.dumps({
            "directory": str(path),
            "files_analyzed": len(results),
            "total_lines": total_lines,
            "total_issues": total_issues,
            "average_quality": round(avg_quality, 2),
            "files": results
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

def get_code_suggestions(filepath: str) -> str:
    """Get specific improvement suggestions for a Python file.
    
    Args:
        filepath: Path to Python file
    
    Returns:
        JSON array of actionable suggestions
    """
    try:
        analysis = analyze_code_file(filepath)
        data = json.loads(analysis)
        
        if "error" in data:
            return analysis
        
        suggestions = data.get("suggestions", [])
        
        # Add general suggestions based on metrics
        metrics = data.get("metrics", {})
        if metrics.get("lines", 0) > 500:
            suggestions.append("File is quite large - consider splitting into multiple modules")
        
        if metrics.get("functions", 0) == 0 and metrics.get("classes", 0) == 0:
            suggestions.append("No functions or classes found - consider structuring code better")
        
        if data.get("quality_score", 0) < 50:
            suggestions.append("Quality score is low - focus on fixing errors and warnings first")
        
        return json.dumps({
            "file": data.get("file"),
            "quality_score": data.get("quality_score"),
            "suggestions": suggestions,
            "suggestion_count": len(suggestions)
        }, indent=2)
        
    except Exception as e:
        return json.dumps({"error": str(e)})

def register(registry):
    registry.register(ToolDef(
        name="analyze_code_file",
        description="Analyze a Python file for code quality issues, metrics, and best practices. Returns detailed report with issues, suggestions, and quality score.",
        parameters={
            "properties": {
                "filepath": {"type": "string", "description": "Path to Python file to analyze"}
            },
            "required": ["filepath"]
        },
        func=analyze_code_file
    ))
    
    registry.register(ToolDef(
        name="analyze_directory",
        description="Analyze all Python files in a directory. Returns summary report with file-by-file quality metrics.",
        parameters={
            "properties": {
                "dirpath": {"type": "string", "description": "Path to directory to analyze"},
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to analyze subdirectories",
                    "default": True
                }
            },
            "required": ["dirpath"]
        },
        func=analyze_directory
    ))
    
    registry.register(ToolDef(
        name="get_code_suggestions",
        description="Get specific, actionable improvement suggestions for a Python file based on static analysis.",
        parameters={
            "properties": {
                "filepath": {"type": "string", "description": "Path to Python file"}
            },
            "required": ["filepath"]
        },
        func=get_code_suggestions
    ))