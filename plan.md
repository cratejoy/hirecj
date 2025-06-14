
# Code Duplication Audit & Consolidation Plan

## 1. Audit Summary

The codebase contains significant duplication of shared code between the `agents` and `auth` services, as well as between the `editor` and `homepage` frontend applications. This violates the DRY (Don't Repeat Yourself) principle and makes maintenance difficult and error-prone.

### Backend Duplication (`agents` vs. `auth`)

The following files are identical or functionally identical across services and should be consolidated into a single shared library.

**Identical Files:**
*   `shared/db_models.py`
*   `shared/config_base.py`
*   `shared/logging_config.py`
*   `shared/env_loader.py`
*   `shared/user_identity.py`
*   `shared/models/api.py`
*   `shared/detect_tunnels.py`
*   `shared/constants.py`

### Frontend Duplication (`editor` vs. `homepage`)

The UI component library appears to have been copied into multiple frontend applications.

**Identical Files:**
*   `editor/src/components/ui/button.tsx`
*   `homepage/src/components/ui/button.tsx`

This indicates other UI components are likely also duplicated.

## 2. Consolidation Plan

The following plan will centralize all shared code, remove duplication, and improve maintainability.

### Step 1: Create a Top-Level `shared` Python Library

A new directory named `shared` will be created at the root of the monorepo. This will become the single source of truth for all shared Python code.

### Step 2: Consolidate Shared Code

All duplicated Python modules from `agents/shared` and `auth/shared` will be moved into the new top-level `shared` library. The `constants.py` files, while identical, will also be moved, with a plan to merge other constants into them in the future.

### Step 3: Delete Redundant Directories

The old `agents/shared` and `auth/shared` directories will be deleted from the repository.

### Step 4: Address Frontend Duplication

As a first step, the duplicated `button.tsx` in the `editor` will be removed. A more comprehensive frontend refactoring should be undertaken to create a shared UI library for all frontend applications.

### Step 5: Update Service Dependencies

The `agents` and `auth` services will be configured to use the new shared library. The existing `sys.path` modifications in the `config.py` files are sufficient to make the new top-level `shared` directory importable, so no code changes are required for imports.

For a more robust setup, each service should install the shared library in editable mode. This can be done by running the following command from within each service's directory (e.g., from `agents/`):
`pip install -e ../shared`

This ensures that changes to the shared library are immediately available to the services during development.
