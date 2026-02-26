# Runbook Command Review & Approve – Implementation Checklist

Use this with **RUNBOOK_REVIEW_IMPLEMENTATION_SPEC.md** for file-level and API details.

---

## Phase 1: Persist per-step validation & review state

- [ ] **Validation pipeline** (`validation_pipeline.py`): After writing `invalid_commands` / `diagnostic_mislabeled` into `spec["meta_data"]`, also set on each step/precheck/postcheck item: `command_validation_status`, `command_validation_issue`, `command_suggested_fix`, `command_review_status`. Set runbook-level `command_review_required` when any step is invalid.
- [ ] Ensure the enriched spec is what gets saved in `Runbook.meta_data` when the runbook is created (already the case if spec is `runbook_spec` inside meta_data).

---

## Phase 2: Approve runbook only when review complete

- [ ] **Runbook controller** (`runbook_controller.py`): Before `approve_and_index_runbook()`, if not `force_approval`, compute “all steps approved for command review” from `meta_data.runbook_spec`; if not complete, return 403 with `code: "command_review_required"`, `message`, `steps_pending_review`.
- [ ] Optional: Add `_is_command_review_complete(meta_data)` helper and/or GET review-status endpoint.

---

## Phase 3: Frontend – review UI and Approve button

- [ ] **GenerateRunbookModal**: Parse validation state from `runbook.meta_data.runbook_spec` (and optional GET review-status). Show banner when there are invalid/unreviewed steps. Disable “Approve runbook” when `!command_review_ready`; handle 403 and show message.
- [ ] **Step-level actions**: Add “Approve step,” “Use suggested command,” “Redo command” (handlers call new endpoints and refresh runbook). Optionally add a “Command review” card listing invalid steps with issue, suggested_fix, and buttons.
- [ ] **RunbookGenerator.tsx**: Same logic for review state and Approve button (and step actions if that view shows runbook detail).

---

## Phase 4: Backend – step approve, update command, regenerate

- [ ] **POST steps/approve**: Set `command_review_status = "approved_by_human"` for the step; persist meta_data (and optionally body_md); return runbook.
- [ ] **PUT steps/command**: Update step command; set `command_validation_status = "pending_review"`; persist meta_data and body_md; return runbook.
- [ ] **POST steps/regenerate**: Regenerate single step command with human_context (new generator method or helper); re-validate; update step fields; persist and return runbook.
- [ ] **Optional GET review-status**: Return `command_review_ready`, `steps_pending_review`, `steps[]` for UI.

---

## Phase 5: API and schemas

- [ ] **Runbooks router**: Register POST steps/approve, PUT steps/command, POST steps/regenerate, GET review-status (see spec for paths and bodies).
- [ ] **api-config.ts**: Add `runbookStepApprove`, `runbookStepUpdateCommand`, `runbookStepRegenerate`, `runbookReviewStatus`.

---

## Phase 6: Testing and docs

- [ ] Manual test: Generate runbook that triggers invalid commands; confirm review UI, disabled Approve, step approve / use suggested / redo; then approve runbook.
- [ ] Add short doc: “Command validation and runbook approval” (when to review, how to approve steps, use suggested command, redo with context).

---

**Order:** 1 → 2 → 4 (step approve only) → 3 (show validation + disable Approve + Approve step) → 4 (update command, regenerate) → 3 (Use suggested, Redo) → 5 → 6.
