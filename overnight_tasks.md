# Jarvis Overnight Improvement Tasks

## Batch 1: 50 Tasks (Priority Order)

### Critical Security & Stability
- [x] 1. Add max_turns limit to conversation loop to prevent infinite tool-calling loops
- [x] 2. Fix stats endpoint hardcoded tool count (shows 16 instead of actual 39+)
- [x] 3. Fix memory thread safety — add lock to get_summary() in session_manager
- [x] 4. Fix OpenAI backend system message duplication on repeated send() calls
- [x] 5. Add conversation message history truncation to prevent token overflow

### Core Architecture Improvements
- [ ] 6. Add structured logging with Python logging module (replace all print statements)
- [ ] 7. Add tool argument validation against schema before execution
- [ ] 8. Add configurable tool timeouts via config.yaml
- [ ] 9. Add token counting to conversation to track usage
- [ ] 10. Add retry logic with exponential backoff for backend API calls

### Error Handling & Resilience
- [ ] 11. Add graceful error handling for Config.load() failures in agent.py
- [ ] 12. Add truncation indicator when tool results are cut off
- [ ] 13. Fix WebConversation tool result truncation to show truncation notice
- [ ] 14. Add error recovery for browser tool initialization failures
- [ ] 15. Add disk space check before file write operations

### Testing Foundation
- [ ] 16. Create tests/ directory with pytest configuration (conftest.py, pytest.ini)
- [ ] 17. Add unit tests for ToolRegistry (register, get, handle_call, schema generation)
- [ ] 18. Add unit tests for Config loading (valid, missing key, invalid backend)
- [ ] 19. Add unit tests for Memory (save_learning, get_relevant, get_summary)
- [ ] 20. Add unit tests for Conversation class (send, clear, message management)

### API Improvements
- [ ] 21. Add request/response logging middleware to FastAPI
- [ ] 22. Add rate limiting with slowapi on chat endpoint
- [ ] 23. Add proper health check that verifies backend connectivity
- [ ] 24. Add session expiration and cleanup (sessions older than 24h)
- [ ] 25. Add pagination to learnings endpoint (limit/offset)

### Web Frontend Fixes
- [ ] 26. Add React error boundary component for graceful crash handling
- [ ] 27. Fix useChat hook missing dependency in useCallback
- [ ] 28. Add loading skeleton to chat while waiting for response
- [ ] 29. Add error toast/notification system for API failures
- [ ] 30. Add keyboard shortcut Ctrl+Enter for send (in addition to Enter)

### Code Quality
- [ ] 31. Create .env.example with all required environment variables documented
- [ ] 32. Add pyproject.toml with project metadata and tool configs (black, ruff, pytest)
- [ ] 33. Fix inconsistent error return patterns — standardize across all tools
- [ ] 34. Add __all__ exports to all __init__.py files
- [ ] 35. Remove duplicate _analyze_image helper (exists in both computer.py and browser.py)

### New Capabilities
- [ ] 36. Add clipboard read/write tools (get_clipboard, set_clipboard)
- [ ] 37. Add file search tool (search across files by content, like grep)
- [ ] 38. Add system_info tool (CPU, RAM, disk, OS details)
- [ ] 39. Add process_manager tool (list processes, kill process)
- [ ] 40. Add download_file tool (download URL to local path with progress)

### Performance
- [ ] 41. Add LRU cache for repeated tool calls with same arguments
- [ ] 42. Cache memory summary — invalidate only on new learning
- [ ] 43. Add async support to web search tool for faster results
- [ ] 44. Lazy-load computer/browser tools (don't import pyautogui until first use)
- [ ] 45. Add connection pooling for Anthropic API client

### Documentation & DevEx
- [ ] 46. Create comprehensive README.md for the project
- [ ] 47. Add docstrings to all public functions in backends
- [ ] 48. Create CONTRIBUTING.md with development setup guide
- [ ] 49. Add API endpoint documentation comments to all routers
- [ ] 50. Create architecture diagram in docs/architecture.md
