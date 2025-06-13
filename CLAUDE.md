## ⚠️ CRITICAL: Definition of Success

**Success is NOT just completing the task.**

Success is completing the task **elegantly and completely** according to our North Star Principles. 

- ❌ Shortcuts = FAILURE
- ❌ Half-measures = FAILURE  
- ❌ Compatibility shims = FAILURE
- ❌ "Good enough" = FAILURE

**Only elegant, complete solutions that fully embody our principles count as success.**

## 🌟 North Star Principles

1. **Simplify, Simplify, Simplify**: Every decision should make the code simpler, not more complex
   - This means: Don't add features we don't need yet
   - This does NOT mean: Remove existing requirements or functionality
   - Keep what's needed, remove what's not
2. **No Cruft**: Remove all redundant code, validation, and unnecessary complexity
3. **Break It & Fix It Right**: No backwards compatibility shims - make breaking changes and migrate properly
4. **Long-term Elegance**: Choose performant, compiler-enforced solutions that prevent subtle bugs
5. **Backend-Driven**: Let the backend handle complexity, frontend should be a thin client
6. **Single Source of Truth**: One pattern, one way to do things, no alternatives
7. **No Over-Engineering**: Design for current needs only - no hypothetical features, no "maybe later" code
8. **Thoughtful Logging & Instrumentation**: We value visibility into system behavior with appropriate log levels
   - Use proper log levels (debug, info, warning, error)
   - Log important state changes and decisions
   - But don't log sensitive data or spam the logs

## 🤖 Operational Guidelines

- When the server needs to be restarted simply stop and ask me to do it.
- **No Magic Values**: Never hardcode values inline. Use named constants, configuration, or explicit parameters
  - ❌ `if count > 10:` 
  - ✅ `if count > MAX_RETRIES:`
- **No Unsolicited Optimizations**: Only implement what was explicitly requested
  - Don't add caching unless asked
  - Don't optimize algorithms unless asked
  - Don't refactor unrelated code unless asked
  - If you see an opportunity for improvement, mention it but don't implement it
- **NEVER Create V2 Versions**: When asked to add functionality, ALWAYS update the existing code
  - ❌ Creating `analytics_lib_v2.py`, `process_data_v2.py`, `utils_v2.py`, etc.
  - ❌ Creating `models_v2.py` or `schema_v2.py`
  - ❌ Creating `test_script_v2.py` or any `_v2` variant
  - ✅ Adding new functions to existing files
  - ✅ Updating existing functions to support new parameters
  - ✅ Refactoring existing code to handle new requirements
  - Exception: Only create a new version if EXPLICITLY asked "create a v2" or "make a new version"
- **Clean Up When Creating PRs**: When asked to create a pull request, ALWAYS:
  - Remove any test files that are no longer needed
  - Delete orphaned or superseded libraries
  - Clean up temporary scripts
  - Ensure no duplicate functionality remains
  - The PR should be clean and ready to merge

## 🚨 Debugging & Problem Solving Guidelines

- **NO LAZY NETWORK ASSUMPTIONS**: Never conclude that errors are due to ngrok, network conditions, packet loss, or "transient network errors"
  - These are lazy explanations that avoid real debugging
  - Always investigate the actual code logic, configuration, and data flow
  - Network issues are extremely rare - 99% of problems are code bugs
- **NO MAGICAL THINKING**: Don't attribute problems to mysterious external forces
  - Look at logs, trace the code path, examine the data
  - Every error has a specific, deterministic cause in the code
  - Find the root cause, don't paper over it with retries or timeouts
