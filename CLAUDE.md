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