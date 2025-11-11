# Supply-Chain Hardening

This document captures the minimum controls required to make the agent stack tamper-evident and aligned with enterprise supply-chain expectations.

## 1. Image Signing With Cosign

1. **Create per-environment signing keys**
   - Generate a key pair for each environment (dev/stage/prod)  
     ```bash
     COSIGN_PASSWORD="" cosign generate-key-pair k8s://troubleshooting-agent/${ENV}
     ```
   - Store private keys in the organization’s secret manager (Vault, AWS KMS, Azure Key Vault). Public keys live in the repo under `infra/keys/`.

2. **Sign images during CI**
   - After building `backend`, `worker`, and `frontend` containers, run:
     ```bash
     cosign sign --key k8s://troubleshooting-agent/${ENV} \
       ghcr.io/example/troubleshooting-agent/backend:${GIT_SHA}
     ```
   - Store the attestation (SLSA provenance, SBOM) alongside the signature:
     ```bash
     cosign attest --predicate build_provenance.json \
       --type slsaprovenance \
       --key k8s://troubleshooting-agent/${ENV} \
       ghcr.io/example/troubleshooting-agent/backend:${GIT_SHA}
     ```
    - Generate and attach an SPDX SBOM predicate so Kyverno can enforce `require-sbom-attestation`:
      ```bash
      syft dir:./backend -o spdx-json > build_provenance.sbom.json
      cosign attest --predicate build_provenance.sbom.json \
        --type https://spdx.dev/Document \
        --key k8s://troubleshooting-agent/${ENV} \
        ghcr.io/example/troubleshooting-agent/backend:${GIT_SHA}
      ```

3. **Verify before rollout**
   - CD pipeline must block promotion unless:
     ```bash
     cosign verify --key infra/keys/prod.pub \
       ghcr.io/example/troubleshooting-agent/backend:${GIT_SHA}
     ```
     succeeds for each image.

4. **SBOM enforcement**
   - CI publishes SPDX SBOM via `syft`:
     ```bash
     syft packages ghcr.io/.../backend:${GIT_SHA} -o spdx-json > sbom/backend-${GIT_SHA}.json
     ```
   - Store SBOM artefacts in an immutable bucket (`s3://troubleshooting-agent-sbom/`).

## 2. Admission Policies (OPA / Kyverno)

Two complimentary policy engines keep unsigned or unverified images out of clusters:

- `infra/policies/kyverno/verify-signed-images.yaml` – cluster admission policy requiring Cosign signatures.
- `infra/policies/kyverno/require-sbom-attestation.yaml` – blocks workloads that are missing an SPDX SBOM attestation signed by the trusted workflow.
- `infra/policies/opa/verify_signatures.rego` – Gatekeeper template equivalent for environments that already run OPA.

Enforce *at least one* of these policies on every runtime cluster. For multi-cluster footprints, attach the policy bundle through GitOps.

## 3. Build Pipeline Hardening

- Lock CI runners to hardened base images; enable ephemeral runners for privileged stages.
- Run container builds inside an isolated network segment; disallow outbound internet except to vetted registries.
- Use dependency scanning (`pip-audit`, `npm audit`, `bandit`) as part of CI; fail builds on critical vulnerabilities.
- Capture provenance with [SLSA Build Levels](https://slsa.dev/); the attestation above is Level 2 compliant.

## 4. Developer Workflow Changes

- Require developers to run `pre-commit` hooks that build SBOM snippets and run static analysis prior to pushing.
- Enforce mandatory code-owner review on Dockerfiles, GitHub Actions, and Terraform modules.
- Rotate signing keys quarterly; revoke compromised keys through Cosign’s Rekor transparency log.

## 5. Monitoring & Alerting

- Emit metrics on signature verification failures (`supply_chain_signature_failures_total`).
- Configure alerting so any unsigned image attempt triggers paging for SRE / Security.
- Periodically (weekly) sample running pods and re-verify signatures & SBOM drift.

## 6. Next Steps

1. Wire Cosign to existing GitHub Actions / GitLab pipelines.
2. Enable Kyverno or Gatekeeper policies using manifests in `infra/policies/`.
3. Add automated SBOM diffing to release checklist and DR exercises.


