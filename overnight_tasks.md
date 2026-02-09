# Jarvis Overnight Improvement Tasks

## Completed (Batch 1)
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

## Completed (Batch 2)
- [x] 1. JWT_SECRET warning on insecure default
- [x] 2. SSRF protection in web fetch (block internal IPs)
- [x] 3. Filesystem path validation (prevent directory traversal)
- [x] 4. Shell command safety layer (warn on destructive commands)
- [x] 5. Disk space check before file writes
- [x] 6. Input size limits on API chat endpoint
- [x] 7. Rate limiting middleware (slowapi)
- [x] 8. Config value validation on load
- [x] 9. Extract duplicate _analyze_image into jarvis/vision.py
- [x] 10. Use config model name in vision tools
- [x] 12. Add __all__ exports to all __init__.py files
- [x] 13. Create .env.example
- [x] 14. Add pyproject.toml
- [x] 15. Replace print() with logging in agent.py
- [x] 16. Add type hints to all public functions
- [x] 17-19. Backend unit tests (Claude, OpenAI, Gemini)
- [x] 20-21. Filesystem and shell tool tests
- [x] 22. Web tool tests (mocked HTTP, SSRF)
- [x] 23. WebConversation tests
- [x] 24-27. API endpoint tests (auth, chat, stats, learnings, sessions)
- [x] 28. Integration tests (full conversation flow)
- [x] 29. Session expiration with 24-hour TTL
- [x] 30. Cache memory summary
- [x] 31. Lazy-load computer/browser tools
- [x] 32. Tool categories in ToolDef
- [x] 33. Deep health check (backend connectivity)
- [x] 34. Request/response logging middleware
- [x] 35. Pagination on learnings endpoint
- [x] 36. Graceful shutdown with 503 rejection
- [x] 37. system_info plugin
- [x] 38. file_search plugin
- [x] 39. clipboard plugin
- [x] 40. download_file plugin
- [x] 41. process_manager plugin
- [x] 42. archive plugin
- [x] 43. env_vars plugin
- [x] 44. http_request plugin
- [x] 45. Tool execution timing and stats
- [x] 46. Token usage tracking across all backends
- [x] 47. Tool usage statistics (calls, errors, avg duration)
- [x] 48. Smart web content truncation
- [x] 50. Startup time profiling
- [ ] ~~49. Backend response caching~~ (skipped: not suitable for conversational AI)

## Batch 3: 50 Tasks (Priority Order)

### Tier 1: Multi-Agent & Planning (1-8)
- [ ] 1. Add task planner: decompose complex requests into sub-tasks
- [ ] 2. Add tool chaining: let agent compose tool outputs as inputs
- [ ] 3. Add parallel tool execution (async tool calls)
- [x] 4. Add conversation branching (save/restore conversation checkpoints)
- [x] 5. Add auto-retry failed tool calls with adjusted parameters
- [ ] 6. Add context window management (smart message summarization)
- [ ] 7. Add streaming responses from backend to API (SSE for partial results)
- [x] 8. Add conversation templates (pre-built system prompts for common tasks)

### Tier 2: API & Web UI Enhancements (9-18)
- [ ] 9. Add WebSocket support for real-time chat
- [x] 10. Add file upload endpoint (accept files for processing)
- [x] 11. Add conversation export (download as JSON/Markdown)
- [ ] 12. Add conversation search (full-text search across history)
- [ ] 13. Add user preferences endpoint (theme, default model, etc.)
- [x] 14. Add API versioning (v1 prefix, version header)
- [ ] 15. Add OpenAPI documentation improvements (examples, tags)
- [ ] 16. Add webhook notifications (POST to URL on task completion)
- [ ] 17. Add batch chat endpoint (process multiple messages)
- [ ] 18. Add admin endpoints (list all users, system stats, config reload)

### Tier 3: Security & Auth Improvements (19-26)
- [ ] 19. Add API key authentication (alternative to JWT for programmatic access)
- [ ] 20. Add role-based access control (admin, user, viewer roles)
- [ ] 21. Add request signing/HMAC for sensitive operations
- [x] 22. Add audit logging (who did what, when)
- [x] 23. Add input sanitization middleware (strip dangerous HTML/scripts)
- [ ] 24. Add tool permission system (restrict which tools users can access)
- [ ] 25. Add secrets management (encrypted storage for API keys)
- [x] 26. Add CORS configuration from env vars (not hardcoded)

### Tier 4: Monitoring & Reliability (27-34)
- [ ] 27. Add Prometheus metrics endpoint (/metrics)
- [x] 28. Add structured JSON logging option (for log aggregation)
- [ ] 29. Add circuit breaker for backend API calls
- [ ] 30. Add dead letter queue for failed tool executions
- [ ] 31. Add health check dashboard endpoint (HTML page)
- [ ] 32. Add error rate tracking and alerting thresholds
- [x] 33. Add request tracing (correlation IDs across logs)
- [ ] 34. Add memory usage monitoring and alerts

### Tier 5: Developer Experience (35-42)
- [x] 35. Add CLI command: `jarvis tools` (list all available tools)
- [ ] 36. Add CLI command: `jarvis test-tool <name>` (test a specific tool)
- [ ] 37. Add plugin scaffolding command: `jarvis new-plugin <name>`
- [ ] 38. Add hot-reload for plugins (watch filesystem for changes)
- [x] 39. Add tool documentation generator (auto-generate from ToolDef)
- [x] 40. Add configuration validation CLI: `jarvis check-config`
- [ ] 41. Add benchmarking suite (measure tool and backend performance)
- [x] 42. Add development mode with verbose logging and debug info

### Tier 6: Advanced Features (43-50)
- [ ] 43. Add cron-style scheduled tasks (run tools on a schedule)
- [x] 44. Add tool result caching (cache expensive tool outputs with TTL)
- [ ] 45. Add multi-model routing (use different models for different tasks)
- [x] 46. Add conversation summarization (compress long conversations)
- [ ] 47. Add tool dependency declaration (tool A requires tool B's output)
- [x] 48. Add plugin marketplace manifest (version, author, dependencies)
- [ ] 49. Add A/B testing framework for prompts and models
- [x] 50. Add cost tracking and budget limits per user/session
