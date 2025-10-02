# Akashic Overlay — All‑in‑One Patch (Namespaced Learning + Canonical LOINC + AWS + CI)

This overlay is **additive**: you can drop these files into your repo and replace existing ones where paths match.
If your repo already has files with these names, **back them up first**.

## What’s included
1) **Namespaced learning** (`context::term`) in `app/learning.py` and wired in `app/main.py` `/api/commit_selection`.
2) **Canonical LOINC chooser** in `app/extensions/canonical_loinc.py` used by `/lookup` for labs.
3) **Smoke scripts**:
   - `smoke.ps1` — core health+lookup+learn
   - `smoke_context.ps1` — verifies namespaced learning (no cross‑talk)
4) **CI Smoke** (GitHub Actions) in `.github/workflows/ci-smoke.yml` (runs boot + curl checks on Linux).
5) **AWS cutover**:
   - **Lambda container** in `aws/lambda/` (Dockerfile + handler + deploy notes).
   - **ECS Fargate** in `aws/ecs/` (Dockerfile + run notes).

## Drop‑in instructions
1. From the root of your repo, unzip the archive and allow overwrite of matching paths:
   ```powershell
   Expand-Archive -Path .\akashic_overlay_all_in_one.zip -DestinationPath . -Force
   ```

2. (Optional) Create data dirs if you don’t have them:
   ```powershell
   mkdir data\logs\learned -ea 0 | Out-Null
   ```

3. Install Python deps (if needed):
   ```powershell
   pip install -r requirements.txt
   ```

4. Local run:
   ```powershell
   uvicorn app.main:app --reload --port 8000
   ```

5. Smokes:
   ```powershell
   powershell -NoProfile -ExecutionPolicy Bypass -File .\smoke.ps1
   powershell -NoProfile -ExecutionPolicy Bypass -File .\smoke_context.ps1
   ```

## Notes
- The `/lookup` endpoint in this overlay includes a **small built‑in canonical set** for quick testing:
  - Hemoglobin → **718-7**
  - Creatinine → **2160-0**
  - LDL cholesterol → **2089-1**
- SNOMED test mappings included:
  - “heart attack” → **22298006** (Myocardial infarction)
  - “watery eyes” / “tearing” → **231834007** (Epiphora)
  - “high blood pressure” → **38341003** (Hypertension)

Adjust/expand as needed to line up with your full JSON datasets.
