# Runbook Command Review & Approve – Detailed Implementation Spec

This document specifies file-by-file changes, data shapes, and API contracts for the fail-safe runbook approval flow (command validation review + human-in-the-loop + Approve runbook gate + Redo command with human context).

---

## 1. Data Structures

### 1.1 Per-step validation/review (stored in runbook)

**Location:** Inside `Runbook.meta_data` → `runbook_spec` (the `spec` dict that is persisted). We add a **parallel structure** so the UI can look up by (section, index) without mutating step objects if we prefer. Recommended: add fields **on each step/precheck/postcheck item** so one source of truth.

**On each item in `spec["prechecks"]`, `spec["steps"]`, `spec["postchecks"]`:**

| Field | Type | Meaning |
|-------|------|--------|
| `command_validation_status` | `"valid"` \| `"invalid"` \| `"pending_review"` | Set by validation pipeline; `invalid` = failed _validate_command_existence or diagnostic_mislabeled. |
| `command_validation_issue` | `string` \| `null` | Message from validator (e.g. "Command not found in documentation"). |
| `command_suggested_fix` | `string` \| `null` | From validator: `suggested_fix` (invalid_commands) or `suggested_fix` (diagnostic_mislabeled). |
| `command_review_status` | `"pending"` \| `"approved_by_human"` \| `"rejected"` | Human review; default `"pending"`. |

**Runbook-level (in `spec` or in `meta_data` at top level):**

| Field | Type | Meaning |
|-------|------|--------|
| `command_review_required` | `boolean` | `true` if any step has `command_validation_status === "invalid"` or `"pending_review"` and `command_review_status !== "approved_by_human"`. |

**Note:** Existing `invalid_commands` / `diagnostic_mislabeled` in `spec["meta_data"]` stay for backward compatibility and for the UI to list “all issues.” The per-step fields above are the source of truth for “can we approve the runbook?”

### 1.2 Existing validator output (reference)

- `RunbookCommandValidator.validate_runbook_commands()` returns:
  - `invalid_commands`: list of `{ "section": "precheck"|"steps"|"postchecks", "index": 1-based, "command", "issue", "suggested_fix", ("name" for steps) }`
  - `diagnostic_mislabeled`: same shape, `suggested_fix` from `suggested_remediation`
- Validation pipeline already writes these into `spec["meta_data"]["invalid_commands"]` and `spec["meta_data"]["diagnostic_mislabeled"]` (see `validation_pipeline.py` lines 191–202).

---

## 2. Backend Changes (by file)

### 2.1 `backend/app/services/runbook/generation/validation_pipeline.py`

**Function:** `validate_commands()`

**After** the block that sets `spec["meta_data"]["invalid_commands"]` and `spec["meta_data"]["diagnostic_mislabeled"]` (around lines 189–202):

1. **Build sets of (section, index) that are invalid or mislabeled:**
   - From `invalid_commands`: (`item["section"]`, `item["index"]`) — note validator uses **1-based** index.
   - From `diagnostic_mislabeled`: same.
   - Map each to `{ "issue": item["issue"], "suggested_fix": item.get("suggested_fix") }`.

2. **Normalize section names** to match spec keys: `"precheck"` → prechecks list, `"steps"` → steps list, `"postchecks"` → postchecks list. Validator uses `"section": "precheck"` but spec keys are `"prechecks"`, `"steps"`, `"postchecks"`. So when iterating:
   - section `"precheck"` → list `spec["prechecks"]`, index 0-based = `item["index"] - 1`.
   - section `"steps"` → `spec["steps"]`, index 0-based = `item["index"] - 1`.
   - section `"postchecks"` → `spec["postchecks"]`, index 0-based = `item["index"] - 1`.

3. **For each (section, 0-based index)** in the invalid/mislabeled set, set on the **dict at that index**:
   - `command_validation_status` = `"invalid"`
   - `command_validation_issue` = issue text
   - `command_suggested_fix` = suggested_fix (string or null)
   - `command_review_status` = `"pending"`

4. **For all other precheck/step/postcheck items** (that are not in the set), set:
   - `command_validation_status` = `"valid"`
   - `command_review_status` = `"pending"` (optional, can leave unset and treat as pending)

5. **Set runbook-level flag:** e.g. `spec["command_review_required"] = True` if there is at least one step with `command_validation_status == "invalid"`. (Or compute it when needed; see 2.3.)

**Leave existing behavior unchanged:** still raise HTTPException for `missing_remediation`; still write `invalid_commands` / `diagnostic_mislabeled` into `spec["meta_data"]` for the UI.

---

### 2.2 `backend/app/controllers/runbook_controller.py`

**Function:** `approve_runbook()`

**Location:** Before the call to `self.generator.approve_and_index_runbook(...)` (around line 439).

1. **If `force_approval` is True,** skip the new check (same as duplicate check).
2. **Else:**
   - Load runbook (already loaded as `runbook` above).
   - Parse `runbook.meta_data` (JSON). Get `runbook_spec = meta_data.get("runbook_spec")` or equivalent.
   - If no `runbook_spec`, allow approval (backward compat).
   - **Compute “all steps approved for command review”:**
     - For each of `runbook_spec.get("prechecks", [])`, `runbook_spec.get("steps", [])`, `runbook_spec.get("postchecks", []):` for each item, if `item.get("command_validation_status") == "invalid"` (or `"pending_review"`), then require `item.get("command_review_status") == "approved_by_human"`.
   - If any step is invalid but not approved_by_human, return **403** (or 400) with a JSON body, e.g.:
     - `{"detail": "Command review required", "code": "command_review_required", "message": "N step(s) have invalid or unreviewed commands. Review or approve each step before approving the runbook.", "steps_pending_review": N }`
   - So the frontend can disable the Approve button and show the message.

**Helper (optional but recommended):** Add a private method e.g. `_is_command_review_complete(meta_data: dict) -> tuple[bool, int]` returning `(ready: bool, steps_pending_review: int)` so the same logic can be reused for an optional review-status endpoint.

---

### 2.3 New endpoints (runbooks router)

**File:** `backend/app/api/v1/endpoints/runbooks.py`

**Base path:** `/api/v1/runbooks/demo/{runbook_id}` (same as existing demo runbook endpoints).

**1) Step approve (mark as approved by human)**

- **Path:** `POST /api/v1/runbooks/demo/{runbook_id}/steps/approve`
- **Body (JSON):** `{ "section": "prechecks" | "steps" | "postchecks", "index": number }` — `index` **0-based** in the list.
- **Logic:** Load runbook by id and tenant; parse `meta_data.runbook_spec`; get the list by `section` (prechecks/steps/postchecks); get item at `index`; set `command_review_status = "approved_by_human"`; optionally set `command_validation_status = "valid"` for display; save `meta_data` back to `Runbook` (and optionally regenerate `body_md` from spec so the stored YAML matches). Return updated runbook (e.g. via controller method that returns `RunbookResponse`).
- **Response:** `200` with full runbook response; or `404` if runbook or step not found; `400` if section/index invalid.

**2) Update step command (apply suggested fix)**

- **Path:** `PUT /api/v1/runbooks/demo/{runbook_id}/steps/command`
- **Body (JSON):** `{ "section": "prechecks" | "steps" | "postchecks", "index": number (0-based), "command": string }`
- **Logic:** Update the step’s `command` in the stored spec; set `command_validation_status = "pending_review"` (or optionally call command validator for that one command and set valid/invalid). Persist `meta_data`; regenerate `body_md` from spec (so the code-fence YAML is in sync). Return updated runbook.
- **Response:** `200` with runbook; `404`/`400` as above.

**3) Regenerate step command (redo with human context)**

- **Path:** `POST /api/v1/runbooks/demo/{runbook_id}/steps/regenerate`
- **Body (JSON):** `{ "section": "prechecks" | "steps" | "postchecks", "index": number (0-based), "human_context": string | null }`
- **Logic:**
  - Load runbook and spec from DB.
  - Get issue_description, env, os_type from meta_data / runbook_spec.
  - Call a new service method (e.g. on `RunbookGeneratorService` or a small helper) that:
    - Builds a prompt: “Regenerate only this step’s command. Issue: … . Current command: … . Validation error: … . Human context: … . OS/Env: … . Return only the new command (and optionally name/expected_output).”
    - Calls LLM once, parses result, updates the single step’s `command` (and optionally name/expected_output) in the spec.
  - Re-validate that single command (call `RunbookCommandValidator._validate_command_existence` or `validate_runbook_commands` for a minimal spec with one step) and set that step’s `command_validation_status`, `command_validation_issue`, `command_suggested_fix`, `command_review_status = "pending"`.
  - Persist `meta_data`, regenerate `body_md`, return updated runbook.
- **Response:** `200` with runbook; `404`/`400` as above.

**4) Optional: Review status (for UI to enable/disable Approve)**

- **Path:** `GET /api/v1/runbooks/demo/{runbook_id}/review-status`
- **Response (JSON):** `{ "command_review_ready": boolean, "steps_pending_review": number, "steps": [ { "section", "index", "command_validation_status", "command_review_status", "command_validation_issue", "command_suggested_fix" } ] }` so the frontend doesn’t have to parse the full spec.

Implement these in the runbooks router and call into the runbook controller (add methods like `approve_step()`, `update_step_command()`, `regenerate_step_command()`, `get_review_status()`).

---

### 2.4 Runbook generator (regenerate single step)

**File:** `backend/app/services/runbook/generation/runbook_generator_core.py` (or a new small module under `runbook/generation/`).

**New method:** e.g. `regenerate_step_command(self, runbook_id: int, section: str, index: int, human_context: Optional[str], db: Session) -> Dict[str, Any]`.

- Load runbook by id (need tenant_id; pass from controller). Parse `meta_data.runbook_spec`.
- Resolve list: `prechecks` / `steps` / `postchecks` by `section`; get step at `index`.
- Build prompt (use existing LLM service): include issue_description, env, current command, current validation issue (if any), human_context, and instruction to return only the new command (and optionally name/expected_output) in a structured way (e.g. JSON or YAML block).
- Call LLM; parse; update step["command"] (and optionally name/expected_output); return updated spec so the controller can persist and optionally re-validate.

**Alternative:** Implement the prompt and LLM call inside the controller or a dedicated `RunbookStepRegenerator` service; keep generator_core unchanged and call the validator from the controller after regeneration.

---

### 2.5 Persisting updated spec and body_md

Whenever a step is updated (approve, update command, regenerate), the runbook’s `meta_data` must be updated and saved. If the spec is stored as `meta_data["runbook_spec"]`, then after mutating that spec you must:

1. Serialize: `meta_data["runbook_spec"] = updated_spec` (or the dict that contains runbook_spec).
2. `runbook.meta_data = json.dumps(meta_data)` (if stored as string) or assign the dict if your ORM supports JSON.
3. If the runbook’s `body_md` is generated from the spec (code fence with YAML), regenerate it: `body_md = "# Agent Runbook (YAML)\n\n```yaml\n" + yaml.safe_dump(spec_dict, ...) + "\n```"` and set `runbook.body_md = body_md`.
4. `db.commit()`.

Do this in the controller methods that handle step approve, update command, and regenerate.

---

## 3. Frontend Changes (by file)

### 3.1 API config

**File:** `frontend-nextjs/src/lib/api-config.ts`

Add under the runbooks/demo section (or wherever demo runbook endpoints are):

- `runbookStepApprove: (runbookId: number) => .../demo/${runbookId}/steps/approve`
- `runbookStepUpdateCommand: (runbookId: number) => .../demo/${runbookId}/steps/command`
- `runbookStepRegenerate: (runbookId: number) => .../demo/${runbookId}/steps/regenerate`
- `runbookReviewStatus: (runbookId: number) => .../demo/${runbookId}/review-status`

(Use your existing `baseUrl` and `/api/v1/runbooks` prefix.)

---

### 3.2 GenerateRunbookModal – show validation and gate Approve

**File:** `frontend-nextjs/src/features/tickets/components/GenerateRunbookModal.tsx`

**State to add:**

- Optional: `reviewStatus: { command_review_ready: boolean; steps_pending_review: number; steps: Array<...> } | null` if you use the review-status endpoint; or derive from `runbook.meta_data.runbook_spec` and per-step fields.

**After runbook is set (when showing the success view with Approve button):**

1. **Parse validation state from runbook:**
   - `const meta = runbook.meta_data || {}; const spec = meta.runbook_spec || {}; const specMeta = spec.meta_data || {};`
   - `invalid_commands = specMeta.invalid_commands || []; diagnostic_mislabeled = specMeta.diagnostic_mislabeled || [];`
   - Also read per-step: for each of `spec.prechecks`, `spec.steps`, `spec.postchecks`, read `command_validation_status`, `command_review_status`, `command_validation_issue`, `command_suggested_fix` (or `command_suggested_fix`).

2. **Compute “can approve runbook”:**
   - `command_review_ready` = every step is either `command_validation_status === "valid"` or `command_review_status === "approved_by_human"`.
   - If you have GET review-status, call it when runbook is loaded and use `command_review_ready` from the response.

3. **UI:**
   - **Banner:** If there are any invalid/pending steps not yet approved, show a banner above the runbook content: “This runbook has steps that failed command validation. Review each step before approving.”
   - **Per-step display:** When rendering prechecks/steps/postchecks (if you add a parsed view), show for each step:
     - Current command.
     - If `command_validation_status === "invalid"`: show issue, suggested fix, and actions: [Approve step] [Use suggested command] [Redo command].
   - **Approve runbook button:** Disable when `!command_review_ready`. On click, if backend returns 403 with `code === "command_review_required"`, show `message` and optionally scroll to first unreviewed step.

4. **Handlers:**
   - **Approve step:** POST to `runbookStepApprove(runbook.id)` with `{ section, index }` (0-based index). On success, refresh runbook (e.g. GET runbook by id) and re-compute `command_review_ready`.
   - **Use suggested command:** PUT to `runbookStepUpdateCommand(runbook.id)` with `{ section, index, command: step.command_suggested_fix }`. Refresh runbook.
   - **Redo command:** Show a small modal or inline textarea for “Human context (optional)”; POST to `runbookStepRegenerate(runbook.id)` with `{ section, index, human_context }`. Refresh runbook.

**Where to render steps:** Currently the modal shows `runbook.body_md` in a `<pre>`. You can either:
- Add a “Review commands” section that parses `meta_data.runbook_spec` and renders prechecks/steps/postchecks in a list with the per-step validation and actions; or
- Keep the pre view and add a separate “Command review” card that lists invalid steps (from `invalid_commands` / `diagnostic_mislabeled`) with issue, suggested_fix, and buttons (Approve step, Use suggested command, Redo command). The second option is simpler and reuses existing `invalid_commands` / `diagnostic_mislabeled`; use 0-based index as `index - 1` when calling APIs (validator uses 1-based).

---

### 3.3 RunbookGenerator (standalone runbook flow)

**File:** `frontend-nextjs/src/components/RunbookGenerator.tsx`

Apply the same logic as in GenerateRunbookModal where the runbook is displayed and the Approve button is shown:

- Parse or fetch review status; disable Approve when `!command_review_ready`; show banner and step-level actions if you add a review section there too.

---

## 4. API Contract Summary

| Method | Path | Body | Response |
|--------|------|------|----------|
| POST | `/api/v1/runbooks/demo/{runbook_id}/steps/approve` | `{ "section": "prechecks"\|"steps"\|"postchecks", "index": number }` (0-based) | 200 RunbookResponse |
| PUT | `/api/v1/runbooks/demo/{runbook_id}/steps/command` | `{ "section", "index", "command": string }` | 200 RunbookResponse |
| POST | `/api/v1/runbooks/demo/{runbook_id}/steps/regenerate` | `{ "section", "index", "human_context"?: string }` | 200 RunbookResponse |
| GET | `/api/v1/runbooks/demo/{runbook_id}/review-status` | - | 200 `{ command_review_ready, steps_pending_review, steps }` |
| POST | `/api/v1/runbooks/demo/{runbook_id}/approve` | - | 200 RunbookResponse, or 403 `{ detail, code: "command_review_required", message, steps_pending_review }` |

---

## 5. Implementation Order

1. **Validation pipeline** – Add per-step fields and `command_review_required` (Section 2.1).
2. **Approve gate** – In runbook controller, check review complete before approve (Section 2.2).
3. **Step approve endpoint** – POST steps/approve and controller method (Section 2.3 + 2.5).
4. **Frontend: show validation and disable Approve** – Parse meta_data / review-status, banner, disable button, handle 403 (Section 3.2).
5. **Frontend: Approve step** – Call steps/approve, refresh runbook (Section 3.2).
6. **Update step command endpoint** – PUT steps/command and regenerate body_md (Section 2.3 + 2.5).
7. **Frontend: Use suggested command** – Call steps/command with suggested_fix (Section 3.2).
8. **Regenerate step** – Generator method or helper + POST steps/regenerate (Section 2.4 + 2.3).
9. **Frontend: Redo command** – Form for human_context, call steps/regenerate (Section 3.2).
10. **Optional: GET review-status** – Endpoint and use in UI (Section 2.3 + 3.2).
11. **RunbookGenerator.tsx** – Same review logic and buttons as modal (Section 3.3).
12. **Docs and tests** – Update runbook/ops docs; manual test with invalid-command runbook.

---

## 6. Index Conventions

- **Validator / existing invalid_commands:** Uses **1-based** `index` (e.g. first step = 1).
- **API and spec arrays:** Use **0-based** index in request body and when indexing `spec.prechecks`, `spec.steps`, `spec.postchecks`.
- **Mapping:** When writing per-step fields in validation_pipeline, use `index_0 = item["index"] - 1`. When the frontend calls the API, send `index: index_0` (0-based). When the backend handles the request, use `index` as 0-based.

---

## 7. Suggested Fix Key Name

The validator returns `suggested_fix` in `invalid_commands` and `diagnostic_mislabeled`. In the spec we store it as `command_suggested_fix` on the step. The UI can use either `invalid_commands[].suggested_fix` or the step’s `command_suggested_fix`; keep one source of truth (the step) after validation pipeline has written it there.

---

---

## 8. Backend implementation complete – quick verification

After implementing the backend (Phases 1–5), verify:

1. **Generate a runbook** that triggers invalid commands (e.g. use an issue that produces a PowerShell command on a “Linux” runbook, or a typo in a cmdlet). Confirm the runbook is saved with:
   - `meta_data.runbook_spec.prechecks` / `steps` / `postchecks` entries having `command_validation_status`, `command_review_status`, and optionally `command_validation_issue`, `command_suggested_fix`.
   - `meta_data.runbook_spec.command_review_required === true` when there are invalid steps.

2. **Approve runbook without reviewing:** `POST /api/v1/runbooks/demo/{id}/approve` without having approved steps. Expect **403** with body containing `code: "command_review_required"` and `steps_pending_review`.

3. **GET review-status:** `GET /api/v1/runbooks/demo/{id}/review-status`. Expect `command_review_ready: false`, `steps_pending_review: N`, and `steps[]` with per-step fields.

4. **POST steps/approve:** For one invalid step, `POST .../steps/approve` with `{ "section": "steps", "index": 0 }`. Then GET review-status again; that step should show `command_review_status: "approved_by_human"` and `steps_pending_review` decremented.

5. **Approve runbook after all steps approved:** After marking all invalid steps as approved (or updating commands), `POST .../approve` again. Expect **200** and runbook status `approved`.

6. **PUT steps/command:** Update a step’s command with `{ "section", "index", "command": "new command" }`. Confirm runbook body_md and meta_data updated.

7. **POST steps/regenerate:** Call with `{ "section", "index", "human_context": "Use bash" }`. Confirm the step’s command changed and validation state is pending_review.

---

End of detailed spec. Use this together with `RUNBOOK_REVIEW_IMPLEMENTATION_CHECKLIST.md` (if present) for implementation and tick off items as you go.
