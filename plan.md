
# Code Deduplication & Refactoring Plan

This document tracks the effort to remove duplicated code and improve the maintainability of the monorepo.

## Phase 1: Structural Consolidation (✅ Completed)

This phase focused on centralizing shared modules that were copied across different services.

### Summary of Actions

-   **Consolidated Shared Backend Modules:** The duplicated `agents/shared/` and `auth/shared/` directories were removed. All their content was merged into a single top-level `/shared` library, which is now the single source of truth for shared Python code.
-   **Initial Frontend Cleanup:** The duplicated `editor/src/components/ui/button.tsx` component was removed as a first step towards a unified UI library.
-   **Fixed Intra-File Duplication:** Corrected syntax errors in several shared modules (`__init__.py`, `logging_config.py`, `user_identity.py`) caused by duplicated file content.
-   **Updated Service Dependencies:** The `agents` and `auth` services were configured to import from the new top-level `/shared` library.

---

## Phase 2: Code-Level & Functional Deduplication (Next Steps)

This phase addresses more subtle code-level duplication and functional overlaps that were identified after the initial structural consolidation.

### 1. Backend Deduplication

-   **Intra-File Duplication & Backups**
    -   **Issue:** Several files still contain their entire content duplicated within the same file (e.g., `shared/db_models.py`, `shared/config_base.py`). A redundant `shared/env_loader.py.backup` file also exists.
    -   **Recommendation:**
        -   Edit the affected files to remove the duplicated blocks of code.
        -   Delete the `shared/env_loader.py.backup` file.

-   **Centralize Logging Configuration**
    -   **Issue:** `agents/app/logging_config.py` and `shared/logging_config.py` perform the same root logger configuration.
    -   **Recommendation:** Standardize on the `shared/logging_config.py` version. Delete `agents/app/logging_config.py` and update all imports in the `agents` service to use the shared module.

-   **Consolidate Session Helpers**
    -   **Issue:** Session cookie generation and validation logic is duplicated and has diverged between `auth/app/services/session_cookie.py` and various helpers in the `agents` service (e.g., `agents/app/middleware/load_user.py`).
    -   **Recommendation:** Move the canonical session logic from `auth/app/services/session_cookie.py` to a new `shared/auth/session_cookie.py` file. Refactor both services to import and use this single helper.

-   **Consolidate User Session Lookup**
    -   **Issue:** The logic to find a user's active Shopify domain (`_get_active_shopify_domain`) is implemented differently in `agents/app/platforms/web/session_handlers.py` and `agents/app/services/session_manager.py`.
    -   **Recommendation:** Consolidate this into a single, authoritative function within `agents/app/services/session_manager.py` and have the session handler call it.

-   **Remove Obsolete Tunnel Detector**
    -   **Issue:** `auth/scripts/tunnel_detector.py` is an older, redundant version of the canonical `shared/detect_tunnels.py`.
    -   **Recommendation:** Delete `auth/scripts/tunnel_detector.py` and update any build processes to use the shared script.

### 2. Frontend Deduplication

-   **Consolidate Demo Scripts**
    -   **Issue:** `homepage/src/components/ScriptFlow.tsx` and `homepage/src/components/DemoScriptFlow.tsx` are functionally identical.
    -   **Recommendation:** Choose one canonical version (`DemoScriptFlow.tsx` seems more current) and delete the other, updating any imports.

-   **Centralize `cn` Utility**
    -   **Issue:** The `cn` utility function for Tailwind CSS classes is duplicated in `editor/src/lib/utils.ts` and `homepage/src/lib/utils.ts`.
    -   **Recommendation:** Establish a shared frontend utility package (e.g., in `packages/utils`) and import `cn` from there in both applications.

-   **Abstract Chat Hooks**
    -   **Issue:** The React hooks `useChat` and `useWebSocketChat` contain related logic for message handling and state management.
    -   **Recommendation:** (Lower Priority) Consider refactoring them to use a common underlying hook (`useChatConnection`?) to reduce code duplication.

-   **Create a Shared UI Library**
    -   **Issue:** Many core UI components (e.g., `Input`, `Card`, `Dialog`) are likely duplicated between `editor/src/components/ui/` and `homepage/src/components/ui/`.
    -   **Recommendation:** Perform a full audit of the two `ui` directories and move all common components into a shared UI library (e.g., in `packages/ui`).
