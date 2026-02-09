# Jarvis Overnight Improvement Tasks

## Completed (Previous Batches)
- [x] 1. Add max_turns limit to conversation loop
- [x] 2. Fix stats endpoint hardcoded tool count
- [x] 3. Fix memory thread safety
- [x] 4. Fix OpenAI backend system message duplication
- [x] 5. Add conversation message history truncation
- [x] 6. Add structured logging with Python logging module
- [x] 7. Add tool argument validation against schema
- [x] 8. Add configurable tool timeouts via config.yaml
- [x] 9. Add token counting to conversation
- [x] 10. Add retry logic with exponential backoff for backend API calls
- [x] 11. Add graceful error handling for Config.load() failures
- [x] 12-14. Error handling improvements
- [x] 15. Rate limit retry with 90-second waits across all API callers
- [x] 16-20. Testing foundation (ToolRegistry, Config, Memory, Conversation)

## Batch 2: 50 Tasks (Priority Order)

### Tier 1: Security Hardening (1-8)
- [ ] 1. Require JWT_SECRET env var — fail startup if using default
- [ ] 2. Add SSRF protection to web fetch tool (block internal IPs)
- [ ] 3. Add filesystem path validation (prevent directory traversal)
- [ ] 4. Add shell command safety layer (warn on destructive commands)
- [ ] 5. Add disk space check before file write operations
- [ ] 6. Add input size limits to API chat endpoint
- [ ] 7. Add rate limiting middleware to FastAPI (slowapi)
- [ ] 8. Validate config values on load (max_tokens > 0, timeout > 0, etc.)

### Tier 2: Code Quality & Deduplication (9-16)
- [ ] 9. Extract duplicate _analyze_image into shared jarvis/vision.py
- [ ] 10. Use config model name in vision tools (not hardcoded)
- [ ] 11. Standardize error message format across all tools
- [ ] 12. Add __all__ exports to all __init__.py files
- [ ] 13. Create .env.example documenting all required env vars
- [ ] 14. Add pyproject.toml with tool configs (ruff, pytest, black)
- [ ] 15. Replace print() calls with proper logging in agent.py
- [ ] 16. Add type hints to all public functions missing them

### Tier 3: Testing Expansion (17-28)
- [ ] 17. Add unit tests for ClaudeBackend (mocked API calls)
- [ ] 18. Add unit tests for OpenAIBackend (mocked API calls)
- [ ] 19. Add unit tests for GeminiBackend (mocked API calls)
- [ ] 20. Add unit tests for filesystem tools
- [ ] 21. Add unit tests for shell tools
- [ ] 22. Add unit tests for web tools (mocked HTTP)
- [ ] 23. Add unit tests for WebConversation (enhanced_conversation.py)
- [ ] 24. Add API endpoint tests for auth router
- [ ] 25. Add API endpoint tests for chat router
- [ ] 26. Add API endpoint tests for stats/learnings routers
- [ ] 27. Add tests for session_manager (lifecycle, cleanup)
- [ ] 28. Add integration test: full conversation flow with mock backend

### Tier 4: Architecture Improvements (29-36)
- [ ] 29. Add session expiration/cleanup (TTL-based, configurable)
- [ ] 30. Cache memory summary (invalidate on new learning)
- [ ] 31. Lazy-load computer/browser tools (defer heavy imports)
- [ ] 32. Add tool categories to ToolDef for filtering/grouping
- [ ] 33. Add health check that verifies backend API connectivity
- [ ] 34. Add request/response logging middleware to FastAPI
- [ ] 35. Add pagination to learnings API endpoint
- [ ] 36. Add proper graceful shutdown to API server

### Tier 5: New Tools & Features (37-44)
- [ ] 37. Add system_info tool (CPU, RAM, disk, OS, Python version)
- [ ] 38. Add file_search tool (grep-like content search across files)
- [ ] 39. Add clipboard tools (read/write system clipboard)
- [ ] 40. Add download_file tool (URL to local path)
- [ ] 41. Add process_manager tool (list/kill processes)
- [ ] 42. Add zip/archive tool (create/extract archives)
- [ ] 43. Add environment variable tool (get/set env vars)
- [ ] 44. Add HTTP request tool (make custom API calls with headers/body)

### Tier 6: Performance & Observability (45-50)
- [ ] 45. Add tool execution timing and logging
- [ ] 46. Add conversation token usage tracking and reporting
- [ ] 47. Add tool usage statistics (which tools called most often)
- [ ] 48. Smart web content truncation (at paragraph boundaries)
- [ ] 49. Add backend response caching for identical prompts
- [ ] 50. Add startup time profiling and optimization
