"""Conversation templates: pre-built system prompt configurations for common tasks."""

from dataclasses import dataclass


@dataclass
class ConversationTemplate:
    """A reusable conversation template with a specialized system prompt."""

    name: str
    description: str
    system_prompt_addition: str
    suggested_tools: list[str] | None = None  # Tool categories to prioritize


TEMPLATES: dict[str, ConversationTemplate] = {
    "code-review": ConversationTemplate(
        name="Code Review",
        description="Review code for bugs, security issues, and improvements.",
        system_prompt_addition="""\
## Code Review Mode

You are in code review mode. Focus on:
- Security vulnerabilities (injection, XSS, SSRF, path traversal)
- Logic errors and edge cases
- Performance issues (N+1 queries, memory leaks, unnecessary allocations)
- Code style and readability
- Missing error handling
- Test coverage gaps

For each issue found, provide:
1. Severity (critical/high/medium/low)
2. Location (file:line)
3. Description of the issue
4. Suggested fix with code

Be thorough but prioritize critical issues first.""",
        suggested_tools=["filesystem"],
    ),
    "data-analysis": ConversationTemplate(
        name="Data Analysis",
        description="Analyze data files, generate statistics, and create reports.",
        system_prompt_addition="""\
## Data Analysis Mode

You are in data analysis mode. When working with data:
- Load and inspect the data first (check shape, types, missing values)
- Provide summary statistics before diving into specifics
- Use Python scripts for complex analysis
- Present findings in clear, structured format with numbers
- Create visualizations when they add value
- Always note data quality issues or caveats

Prefer pandas for tabular data, json for semi-structured data.""",
        suggested_tools=["filesystem", "shell"],
    ),
    "devops": ConversationTemplate(
        name="DevOps",
        description="Infrastructure, deployment, CI/CD, and system administration.",
        system_prompt_addition="""\
## DevOps Mode

You are in DevOps mode. Focus on:
- Infrastructure as code (Terraform, CloudFormation, Docker)
- CI/CD pipeline configuration
- Monitoring and alerting setup
- Security hardening and compliance
- Performance optimization
- Disaster recovery planning

Always consider: idempotency, rollback strategies, and least privilege.
Prefer declarative over imperative configurations.""",
        suggested_tools=["shell", "filesystem", "web"],
    ),
    "research": ConversationTemplate(
        name="Research",
        description="Research topics using web search and analysis.",
        system_prompt_addition="""\
## Research Mode

You are in deep research mode. When researching:
- Start with broad searches, then narrow down
- Cross-reference multiple sources
- Distinguish facts from opinions
- Note source credibility and recency
- Organize findings into clear sections
- Provide a summary with key takeaways
- Include source URLs for verification

Be thorough and objective. Present multiple perspectives when relevant.""",
        suggested_tools=["web"],
    ),
    "writing": ConversationTemplate(
        name="Writing Assistant",
        description="Write, edit, and improve documents and content.",
        system_prompt_addition="""\
## Writing Mode

You are in professional writing mode. Focus on:
- Clear, concise language
- Proper structure (intro, body, conclusion)
- Audience-appropriate tone
- Active voice when possible
- Strong transitions between sections
- Fact-checking and accuracy

For editing: preserve the author's voice while improving clarity.""",
        suggested_tools=["filesystem"],
    ),
    "debugging": ConversationTemplate(
        name="Debugging",
        description="Diagnose and fix bugs in code.",
        system_prompt_addition="""\
## Debugging Mode

You are in debugging mode. Follow a systematic approach:
1. Reproduce the issue (understand exact symptoms and steps)
2. Gather evidence (logs, error messages, stack traces)
3. Form hypotheses (most likely causes based on evidence)
4. Test hypotheses (read relevant code, add logging if needed)
5. Identify root cause (not just the symptom)
6. Implement fix (minimal, targeted change)
7. Verify fix (run tests, check for regressions)

Never guess. Always base conclusions on evidence.""",
        suggested_tools=["filesystem", "shell"],
    ),
}


def get_template(name: str) -> ConversationTemplate | None:
    """Get a conversation template by name."""
    return TEMPLATES.get(name)


def list_templates() -> list[dict]:
    """Return all available templates as dicts."""
    return [
        {"name": t.name, "key": key, "description": t.description}
        for key, t in TEMPLATES.items()
    ]
