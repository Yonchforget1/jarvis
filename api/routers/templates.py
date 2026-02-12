"""Prompt templates router – pre-built conversation starters – backed by Supabase."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from api.db import db
from api.deps import UserInfo, get_current_user

log = logging.getLogger("jarvis.api.templates")
router = APIRouter(prefix="/api/templates", tags=["templates"])

# Built-in templates available to all users
BUILTIN_TEMPLATES = [
    {
        "id": "code-review",
        "name": "Code Review",
        "description": "Get a thorough review of your code with suggestions for improvement",
        "category": "Development",
        "icon": "code",
        "prompt": "Please review the following code. Focus on:\n1. Bugs or potential issues\n2. Performance concerns\n3. Code style and readability\n4. Security vulnerabilities\n5. Suggestions for improvement\n\nHere's the code:\n\n",
    },
    {
        "id": "debug-error",
        "name": "Debug Error",
        "description": "Help diagnose and fix an error or bug",
        "category": "Development",
        "icon": "bug",
        "prompt": "I'm encountering an error. Here are the details:\n\nError message: \nLanguage/Framework: \nWhat I was trying to do: \n\nPlease help me understand what's causing this and how to fix it.",
    },
    {
        "id": "write-tests",
        "name": "Write Tests",
        "description": "Generate comprehensive tests for your code",
        "category": "Development",
        "icon": "test",
        "prompt": "Please write comprehensive tests for the following code. Include:\n- Unit tests for each function/method\n- Edge cases\n- Error handling tests\n- Integration tests if applicable\n\nCode:\n\n",
    },
    {
        "id": "explain-code",
        "name": "Explain Code",
        "description": "Get a clear explanation of how code works",
        "category": "Development",
        "icon": "book",
        "prompt": "Please explain the following code in detail. Break down:\n- What it does overall\n- How each section works\n- Any important patterns or techniques used\n- Potential issues or improvements\n\n",
    },
    {
        "id": "business-plan",
        "name": "Business Plan",
        "description": "Draft a business plan or strategy document",
        "category": "Business",
        "icon": "chart",
        "prompt": "Help me create a business plan for the following idea:\n\nBusiness concept: \nTarget market: \nRevenue model: \n\nPlease include sections for executive summary, market analysis, competitive landscape, marketing strategy, financial projections, and key milestones.",
    },
    {
        "id": "email-draft",
        "name": "Professional Email",
        "description": "Draft a professional email for any situation",
        "category": "Communication",
        "icon": "mail",
        "prompt": "Please draft a professional email with the following details:\n\nTo: \nSubject: \nPurpose: \nTone: (formal/casual/diplomatic)\nKey points to cover:\n\n",
    },
    {
        "id": "api-design",
        "name": "API Design",
        "description": "Design a REST API with endpoints and schemas",
        "category": "Development",
        "icon": "api",
        "prompt": "Help me design a REST API for:\n\nProject: \nMain resources: \n\nPlease include:\n- Endpoint definitions (method, path, description)\n- Request/response schemas\n- Authentication approach\n- Error handling patterns\n- Pagination strategy",
    },
    {
        "id": "data-analysis",
        "name": "Data Analysis",
        "description": "Analyze data and extract insights",
        "category": "Data",
        "icon": "chart",
        "prompt": "Please analyze the following data and provide insights:\n\nData description: \nKey questions to answer:\n1. \n2. \n3. \n\nPlease include statistical summaries, trends, and actionable recommendations.",
    },
    {
        "id": "system-design",
        "name": "System Design",
        "description": "Design a software system architecture",
        "category": "Development",
        "icon": "server",
        "prompt": "Help me design a system architecture for:\n\nSystem: \nScale: (users, requests/sec)\nRequirements:\n- \n\nPlease include:\n- High-level architecture diagram (text)\n- Component breakdown\n- Database design\n- API design\n- Scaling strategy\n- Technology choices with rationale",
    },
    {
        "id": "content-write",
        "name": "Content Writing",
        "description": "Write articles, blog posts, or marketing copy",
        "category": "Content",
        "icon": "pen",
        "prompt": "Please write the following content:\n\nType: (blog post/article/marketing copy/social media)\nTopic: \nTarget audience: \nTone: \nLength: \nKey points to include:\n\n",
    },
    {
        "id": "sql-query",
        "name": "SQL Query Builder",
        "description": "Build complex SQL queries from natural language",
        "category": "Data",
        "icon": "database",
        "prompt": "Help me write a SQL query for:\n\nDatabase: (PostgreSQL/MySQL/SQLite)\nTables involved: \nWhat I need: \n\nPlease provide the query with explanation of each part.",
    },
    {
        "id": "shell-automation",
        "name": "Shell Automation",
        "description": "Create shell scripts and automation",
        "category": "DevOps",
        "icon": "terminal",
        "prompt": "Help me create a shell script that:\n\nPlatform: (Linux/macOS/Windows)\nTask: \nRequirements:\n- \n\nPlease include error handling, logging, and comments.",
    },
]


class CreateTemplateReq(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: str = Field("", max_length=500)
    category: str = Field("Custom", max_length=50)
    prompt: str = Field(..., min_length=1, max_length=10000)


@router.get("")
async def list_templates(user: UserInfo = Depends(get_current_user)):
    """List all available templates (built-in + user custom)."""
    rows = db.select("templates", filters={"user_id": user.id})
    custom = []
    for r in (rows or []):
        custom.append({
            "id": r["template_id"],
            "name": r["name"],
            "description": r.get("description", ""),
            "category": r.get("category", "Custom"),
            "prompt": r["prompt"],
            "icon": r.get("icon", "custom"),
            "custom": True,
        })
    builtin = [dict(t, custom=False) for t in BUILTIN_TEMPLATES]
    return builtin + custom


@router.get("/categories")
async def list_categories(user: UserInfo = Depends(get_current_user)):
    """List all template categories."""
    cats = set()
    for t in BUILTIN_TEMPLATES:
        cats.add(t["category"])
    rows = db.select("templates", filters={"user_id": user.id})
    for t in (rows or []):
        cats.add(t.get("category", "Custom"))
    return sorted(cats)


@router.post("")
async def create_template(
    req: CreateTemplateReq,
    user: UserInfo = Depends(get_current_user),
):
    """Create a custom prompt template."""
    count = db.count("templates", filters={"user_id": user.id})
    if count >= 50:
        raise HTTPException(400, "Maximum 50 custom templates per user")

    template_id = uuid.uuid4().hex[:12]
    db.insert("templates", {
        "template_id": template_id,
        "user_id": user.id,
        "name": req.name,
        "description": req.description,
        "category": req.category,
        "prompt": req.prompt,
        "icon": "custom",
    })

    return {
        "id": template_id,
        "name": req.name,
        "description": req.description,
        "category": req.category,
        "prompt": req.prompt,
        "icon": "custom",
        "custom": True,
    }


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    user: UserInfo = Depends(get_current_user),
):
    """Delete a custom template."""
    existing = db.select(
        "templates",
        filters={"template_id": template_id, "user_id": user.id},
        single=True,
    )
    if not existing:
        raise HTTPException(404, "Template not found")
    db.delete("templates", {"template_id": template_id})
    return {"status": "deleted"}
