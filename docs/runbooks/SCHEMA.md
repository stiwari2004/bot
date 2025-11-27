## Runbook YAML Schema

This document describes the canonical structure every auto-generated runbook must follow. It applies to *all* issue types (CPU, memory, disk, network, service, application, etc.).

### Top-Level Fields

| Field | Required | Description |
| --- | --- | --- |
| `runbook_id` | ✅ | Unique identifier, must start with `rb-` |
| `version` | ✅ | Semantic version (e.g., `1.0.0`) |
| `title` | ✅ | Clear, human-readable summary of the issue |
| `service` | ✅ | CI type (server, database, storage, web, network, …) |
| `env` | ✅ | `prod`, `staging`, `dev`, `Windows`, or `Linux` |
| `risk` | ✅ | `low`, `medium`, or `high` |
| `description` | ✅ | Single-line problem statement + impact |
| `inputs` | ✅ | Parameter list (name, type, required, description, default) |
| `prechecks` | ✅ | Exactly 3 diagnostic commands that validate the issue |
| `steps` | ✅ | Exactly 5–6 main actions that diagnose + remediate |
| `postchecks` | ✅ | Exactly 1 command verifying the metric is normal |

### Step-Level Metadata

Every entry inside `steps` now supports richer metadata to help the execution engine behave like a human operator:

| Field | Type | Purpose |
| --- | --- | --- |
| `purpose` | `precheck` \| `diagnose` \| `remediate` \| `postcheck` \| `verify` | Declares the intent of the step so validation can enforce “diagnose → remediate → verify” ordering. At least **3** steps must be `remediate`. |
| `requires_metric` | `str` | Which metric this step expects from prechecks (e.g., `cpu_usage`, `memory_percent`). Used to ensure commands actually target the cited issue. |
| `captures_variable` | `str` | Optional variable name to extract from the step output (e.g., `top_cpu_pid`, `service_name`). |
| `depends_on` | `List[str]` | Names of variables this step requires. Execution stops with a safe failure if any dependency is missing. |
| `skip_in_auto_mode` | `bool` | Already supported; indicates destructive steps that require human approval. |
| `severity` | `safe` \| `moderate` \| `dangerous` | Automatically inferred if omitted. |

**Prechecks/postchecks** keep their existing `description`, `command`, and `expected_output` fields but must align with the same metric identified in the issue description. Inputs **must never** contain commands.

### Validation Rules

1. **Structure**
   - 3 prechecks, 5–6 main steps, 1 postcheck.
   - Inputs must only contain parameter metadata (no commands or `type: command`).

2. **Metric Grounding**
   - First precheck must measure the actual metric reported in the ticket (CPU, memory, disk, network, service availability, etc.).
   - Postcheck must re-measure the same metric to confirm resolution.
   - Each step’s `requires_metric` (when present) must match either the detected issue metric or a derived sub-metric (e.g., `logical_disk_c_percent` for disk issues).

3. **Remediation Obligation**
   - At least 3 steps must have `purpose: remediate`.
   - Purely diagnostic runbooks (all `diagnose`) are rejected as **CRITICAL** failures.

4. **Variable Discipline**
   - `captures_variable` values must be unique per step.
   - Every name referenced in `depends_on` must appear in a prior step’s `captures_variable`.

5. **Flow Assurance**
   - Steps must be ordered `diagnose` → `remediate` → `verify`.
   - Once a remediation step marks the issue resolved, execution can proceed directly to postcheck/closure.

These rules are enforced in `runbook_generator_core.py::_validate_generated_runbook` and covered by unit tests in `backend/tests/unit/test_runbook_validation.py`.




