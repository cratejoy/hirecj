# NOTE: When building plans, clone this template and use it to structure plan

# Feature / Refactor Implementation Plan Template

## North Stars & Principles

### ⚠️ CRITICAL: Definition of Success

Success is **not** simply building something that "works".
Only elegant, complete solutions that fully embody our principles count as success.

* ❌ Shortcuts = **FAILURE**
* ❌ Half‑measures = **FAILURE**
* ❌ Compatibility shims = **FAILURE**
* ❌ “Good enough” = **FAILURE**

### 🌟 Guiding Principles

1. **Long‑Term Elegance Over Short‑Term Hacks** – pick the right, performant, compiler‑enforced solution; prevent subtle bugs.
2. **Break It & Fix It Right** – prefer breaking changes and migrating to a single correct pattern over backwards‑compatibility shims (only add shims if Amir explicitly requests them).
3. **Simplify, Simplify, Simplify** – every decision should make the codebase simpler; lean solutions beat “kitchen‑sink” designs.
4. **Single Source of Truth** – one clear pattern, no alternatives.
5. **No Cruft** – delete redundant code immediately; keep the surface area minimal.
6. **Thoughtful Logging & Instrumentation** – visibility without noise; respect log levels.
7. **Infrastructure as Code** – all infra changes via Terraform; never manual `kubectl scale` or similar commands.
8. **Answer Before You Code** – when Amir asks a question, answer it first, code second.

---

## Do’s ✅ and Do Not’s ❌

### Do’s

* Address Amir by name ("Amir") in all communication.
* Use **`rg`** or **`ag`** for searching the codebase.
* Stage commits interactively; rely on `git status`, **never** `git add .`.
* Thoroughly test fixes locally **before** committing and again before asking Amir to test.
* Use a single scratchpad file **`plan.md`** for planning unless Amir instructs otherwise.
* When Amir asks for a PR, include a comment: `@claude review this`.
* Show the **Terraform** diff/config when infra changes or scaling is required.
* Produce lean, incremental milestones that deliver concrete, usable artifacts.

### Do Not’s

* 🚫 Push commits or open PRs unless Amir explicitly asks for them.
* 🚫 Introduce backwards‑compatibility shims, new features, CI steps, benchmarks, or documentation unless requested.
* 🚫 Commit untested code or code with failing tests without Amir’s permission.
* 🚫 Estimate implementation times – Amir owns scheduling.
* 🚫 Create multiple planning files; stick to **`plan.md`**.
* 🚫 Perform manual infra changes (`kubectl`, console tweaks); use Terraform.
* 🚫 Waste time on docs for unstable POCs; they go stale fast.

---

## 🚧 Implementation Status Banner

> **🚀 CURRENT PHASE:** *Milestone X – Phase Y* 🟡 In Progress
> **🔜 NEXT STEPS:** *Brief description of what’s coming next*

## Executive Summary

> Summarize the problem/opportunity, the proposed solution, and expected impact in 3–5 sentences.

---

## Architecture Snapshot – Before vs. After

### On‑Disk Layout

|                 | **Before**        | **After**           |                   |
| --------------- | ----------------- | ------------------- | ----------------- |
| `/path/to/file` | Brief description | `/new/path/to/file` | Brief description |
| ...             |                   | ...                 |                   |

### Conceptual / Object Hierarchies

|                | **Before** | **After**      |       |
| -------------- | ---------- | -------------- | ----- |
| `Module/Class` | Notes      | `Module/Class` | Notes |
| ...            |            | ...            |       |

---

## Milestones & Phases – Checklist View

* [ ] **Milestone 1 – *Descriptive Name*** 🟡

  * [ ] **Phase 1 – *Name*** 🔴 – deliverable description
  * [ ] **Phase 2 – *Name*** ⬜ – deliverable description
  * **Success Criteria**: bullet list of measurable outcomes

* [ ] **Milestone 2 – *Descriptive Name*** ⬜

  * [ ] **Phase 1 – *Name*** ⬜ – deliverable description
  * ...

---

## Test Plan

* **Unit Tests**: what modules/functions, success thresholds
* **Integration Tests**: cross‑component tests, data fixtures
* **End‑to‑End Scenarios**: user flows, acceptance tests
* **Performance / Regression**: benchmarks, load tests
* **Tooling & CI Hooks**: linting, static analysis, code coverage targets

---

## Target Output API (if applicable)

```jsonc
{
  "endpoint": "/v1/example",
  "request": {
    // example fields
  },
  "response": {
    // example fields
  }
}
```

---

## Detailed Implementation Plan

Break down each milestone and phase with actionable steps, accompanying tests, and acceptance criteria.

### Milestone 1 – *Descriptive Name*

#### Phase 1 – *Name*

* **Implementation Steps**

  * [ ] Step 1: ...
  * [ ] Step 2: ...
* **Test Plan**

  * Unit: ...
  * Integration: ...
* **Success / Acceptance Criteria**

  * ...

#### Phase 2 – *Name*

* **Implementation Steps**

  * [ ] ...
* **Test Plan**

  * ...
* **Success / Acceptance Criteria**

  * ...

---

### Milestone 2 – *Descriptive Name*

<!-- Repeat the same structure for each milestone -->

---

## Glossary / References

* Design doc: `[link]`
* Jira/Epic: `[link]`
* Related RFCs / ADRs: `[link]`

---

## Final Acceptance Checklist

* [ ] All milestone success criteria met
* [ ] Documentation updated
* [ ] Metrics & dashboards live
* [ ] Stakeholder sign‑off obtained

