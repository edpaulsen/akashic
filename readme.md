October 1
Love it. Here’s a tight end-of-day wrap and a pick-your-next-move menu.

### Quick end-of-day checklist

* Run both smokes one last time:

  ```powershell
  powershell -NoProfile -ExecutionPolicy Bypass -File .\smoke.ps1
  powershell -NoProfile -ExecutionPolicy Bypass -File .\smoke_context.ps1
  ```
* Tag is already set. Optional local backup zip:

  ```powershell
  Compress-Archive -Path * -DestinationPath .\repo-backup-pre-aws-context-green.zip -Force
  ```

### Pick what you want to do next (I’ll give surgical patches)

1. **Namespaced learning**
   Keep saved choices separate per field (e.g., `lab.test::hemoglobin` vs `pmh.condition::hemoglobin`).
   *Result:* no cross-talk between labs, problems, procedures.

2. **Canonical LOINC selector**
   Small table for common labs (e.g., Hemoglobin → **718-7**, Creatinine → **2160-0**) so your fallback always picks the gold standard when multiple 100s exist.

3. **AWS cutover (minimal friction)**
   Two paths:

   * **Lambda container**: package FastAPI in a container, deploy via ECR + API Gateway.
   * **ECS Fargate**: run the same container behind an ALB.
     I’ll hand you a copy-paste Terraform or AWS CLI plan referencing this repo layout.

4. **CI smoke**
   Add a GitHub Action that runs a lightweight backend boot + `smoke.ps1` equivalent (Linux) on every commit, so “green stays green”.

Reply with **1, 2, 3, or 4** (or a combo), and I’ll drop the exact “XXX → YYY” changes and files.


Awesome. Repo’s in a good place. Sleep well, Eddie 😴

When you’re back tomorrow, we can pick up with any of these:

1. Namespaced learning (`context::term`) – tiny patch.
2. Canonical LOINC chooser (e.g., Hemoglobin → 718-7).
3. AWS cutover plan (Lambda container or ECS Fargate) using this repo.

Just say **1**, **2**, or **3** and I’ll drop precise, copy-paste steps.



Sept 30
Got it. Here’s the **tight plan for tomorrow**—no code walls, just the exact order of operations.

# Plan for tomorrow

1. **Make JSON loads BOM-proof**

   * In `app/main.py`, change both JSON reads to use `encoding="utf-8-sig"` (so BOMs never break the app).

2. **Add startup safety**

   * Add a small `@app.on_event("startup")` that:

     * `mkdir -p data/logs/learned`
     * creates `data/layman_learned.json` if missing (`{}`)

3. **Rebuild & run (persisting data)**

   * From repo root:

     ```
     docker build -t akashic-lookup-dev:latest .
     docker stop akashic-lookup-dev 2>$null
     docker rm akashic-lookup-dev 2>$null
     docker run -d --name akashic-lookup-dev -p 8000:8000 `
       -e ADMIN_TOKEN=dev `
       --mount type=bind,source="C:\akashic-loinc-mapping\data",target="/app/data" `
       akashic-lookup-dev:latest
     ```

4. **Smoke tests (CLI)**

   * Health:

     ```
     curl.exe -s http://127.0.0.1:8000/api/healthz
     ```
   * Lookup:

     ```
     curl.exe -s "http://127.0.0.1:8000/lookup?q=heart%20attack&domain=auto&include_technical=true"
     ```
   * Save:

     ```
     echo {"term":"heart attack","code":"22298006","display":"Myocardial infarction","lay_text":"heart attack","dry_run":false} > payload.json
     curl.exe -s -X POST "http://127.0.0.1:8000/api/commit_selection" -H "Content-Type: application/json" --data-binary "@payload.json"
     ```
   * Unlearn:

     ```
     curl.exe -s -X POST "http://127.0.0.1:8000/api/unlearn" -H "Content-Type: application/json" --data-binary "{\"term\":\"heart attack\",\"keep_aliases\":true}"
     ```

5. **Verify persistence on host**

   * Check files:

     ```
     dir C:\akashic-loinc-mapping\data
     dir C:\akashic-loinc-mapping\data\logs\learned
     ```
   * Restart and re-check lookup:

     ```
     docker restart akashic-lookup-dev
     curl.exe -s "http://127.0.0.1:8000/lookup?q=heart%20attack&domain=auto&include_technical=false"
     ```

6. **UI sanity (quick)**

   * Search **heart attack** → 4 SNOMED options show pre-save.
   * Search **cholesterol total** → LOINC-only, no SNOMED dropdown.
   * Search **purple giraffe syndrome** → empty/no-match, no crash.

7. **(Optional, after all green)**

   * Add `/api/export_learned` (simple GET returning the JSON).
   * Drop `dev.ps1` (rebuild/restart helper) and `smoke.ps1` (runs the four tests).

That’s it. We’ll execute those steps in order and stop at the first red flag.



September 29:

Perfect stopping point.

# What we accomplished today

* Cleaned `layman_learned.json` to **code-only** (no display strings) and normalized keys.
* Hardened `/api/commit_selection`; added `/api/unlearn`, `/api/export/learned`, `/api/import/learned`.
* Added **seed loader on startup** and a **seed verify** flow.
* Improved UI (buttons, toasts) and added **Unlearn mapping**.
* Created a **Dockerfile**, built the image, and ran the app in a container with the `data/` volume mounted.

# Tomorrow’s plan (we’ll do ONE step at a time)

**Step 1 (next):** Add simple auth (header token) to protect write endpoints: `/api/commit_selection`, `/api/unlearn`, `/api/import/learned`.
If you say “go,” I’ll give you the exact minimal patch (server + a small `.env` read + client header add).

**Later steps (after Step 1, one by one):**
2) Add **/api/export/snapshot** (zip of `data/`), and **/api/import/snapshot** (restore) for backups.
3) AWS path (smallest surface area first):

* Push image to **ECR**,
* Run on **ECS Fargate** behind an ALB,
* Mount learned data via **S3** sync or migrate store to **DynamoDB** (code-only).

4. “AI assist” for suggestions (server-side reranker for SNOMED/LOINC; then optional OpenAI/Azure inference).

# Quick start after a reboot (Docker)

Do these from a regular PowerShell window in your repo root `C:\akashic-loinc-mapping`:

1. **Start Docker Desktop**

```powershell
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
```

2. **Confirm Docker is up**

```powershell
docker version
```

(If you get “not recognized,” new shell usually fixes it; as a fallback you can prepend the bin path:
`$env:Path = "$Env:ProgramFiles\Docker\Docker\resources\bin;$env:Path"`)

3. **Run the container (detached)**

```powershell
docker run -d --rm -p 8000:8000 -v "${PWD}\data:/app/data" --name akashic-dev akashic-loinc-mapping:latest
```

4. **Verify**

* API health: [http://localhost:8000/api/healthz](http://localhost:8000/api/healthz)
* App UI: [http://localhost:8000/](http://localhost:8000/)

5. **Stop**

```powershell
docker stop akashic-dev
```

If you prefer a one-click script, I can hand you `start_dev.ps1` and `stop_dev.ps1` next time as Step 1 instead.

When you’re ready tomorrow: say **“go”** and we’ll do the auth patch as exactly one step.



Got it. You’re all set for today. Here’s a tight plan for our next session so we fix the “fat → observation miss” and remove the LOINC/Condition choice for patients.

# Next-visit plan ( crisp, 1 step at a time )

1. **Add `domain=auto` (default)**

   * Behavior: one search box; we check **layman mappings across both domains** first.
   * If exactly one high-confidence hit → return that.
   * If multiple, return **grouped** results: `condition[]` and `observation[]`.
   * This alone stops “fat” from being logged as a miss just because the wrong domain was selected.

2. **Smart miss logging**

   * Before logging a miss, we’ll **cross-check the other domain**.
   * Only write to `misses.jsonl` if **both** domains fail.
   * Include a `reason` (e.g., `misrouted_observation_had_condition_match`) to keep your analytics clean.

3. **AI normalization (safe & optional)**

   * Add a small `ai_normalize()` step that only runs when both domains fail.
   * Start rule-based (e.g., “fat” → “obesity”, “sugar high” → “hyperglycemia/diabetes”).
   * Later, swap in Bedrock (Claude) to suggest a **normalized phrase** (never a code).
   * If post-normalize there’s **one** high-confidence code → auto-learn it; else log for review.

4. **Auto-learn guardrails**

   * Only auto-add to `layman_learned.json` when:

     * single candidate, score ≥ threshold (e.g., 92),
     * concept in a whitelist (e.g., Obesity, Hypertension, Diabetes).
   * Everything else goes to the review queue (we already have `/teach`).

5. **Patient UI simplification**

   * Default to `auto` mode; **hide the domain selector** from patients.
   * Keep “More (technical)” for clinicians/power users.
   * Practitioner pane still shows the FHIR `CodeableConcept` we’ll store.

6. **Data hygiene**

   * Add a small **dedupe-on-load** for `layman_learned.json` (unique by `(system,code)` + `preferredTerm`).
   * Add `/learned` read endpoint so you can review what’s been learned in the UI.

7. **Quick sanity tests**

   * Queries to verify: `fat` → Obesity (SNOMED), `obese` → Obesity, `high blood pressure` → Hypertension,
     `cholesterol` → 2093-3 (LOINC), `A1c` → 4548-4 (LOINC).
   * Confirm: no miss logged when the other domain had a match.

If you want, I can start with step **1 only** next time: implement `domain=auto` and keep everything else unchanged. Then we’ll test “fat” once and move to step 2.


As of September 18:
Totally fair concern. If this took us hours for 3–4 terms, doing it for 100,000 by hand would be a non-starter. The answer isn’t “let AI magically figure it out,” it’s a **hybrid** that’s boringly reliable:

## What actually scales (no heroics, no manual curation)

1. **Deterministic spine (always-on)**

   * Prefer **SNOMED for symptoms/conditions**, **LOINC for labs**.
   * Tight **token guard**, domain gates, and a **single top result** for patients.
   * **Abstain** when unsure (“We couldn’t confidently match that”) rather than guess wrong.

2. **Terminology services as ground truth**

   * Use FHIR TS for official codes/displays/synonyms.
   * We don’t “invent codes”; AI only helps decide **which** code, never **what** a code is.

3. **AI as a *booster*, not the decider**

   * **Spell/typo/alias normalizer** (cheap model or rules) before matching.
   * **Embeddings reranker** (top-10 candidates from TS + heuristics → reorder), not a free-form LLM answer.
   * **Auto-learn synonyms** only when confidence + margin thresholds are met; otherwise log a miss.
   * Nightly **AI synonym proposals** gated by rules (must semantically match the official concept and pass guardrails) — auto-accepted only when safe; otherwise ignored.

4. **Closed-loop telemetry**

   * Log every query, candidates, score, decision, and whether user clicked/confirmed.
   * Promote/demote learned phrases automatically (e.g., promote after 3+ distinct users; demote if collisions rise).
   * Versioned data with rollback.

## How we’ll know it works (measurable, not vibes)

* **Top-1 accuracy (patient)** on a growing test set.
* **False-positive rate** (irrelevant code shown) — must stay very low.
* **Abstain rate** (we said “not sure”) — acceptable early, should trend down as learning grows.
* **Time-to-learn** (queries until a new synonym becomes stable).

## What we just did today (and why it wasn’t wasted)

Everything we changed (patient single result, token guard, practitioner filters, self-learn write, A1C normalization, lab “pin”) are **general rules** that:

* reduce wrong matches across the board,
* survive when we plug in TS + embeddings,
* keep patients safe by favoring abstain over noisy guesses.

These aren’t one-offs; they’re the rails the AI rides on.

## Pragmatic rollout plan (bite-sized)

* **Now (local):**
  Keep today’s deterministic guardrails; **add spell/alias normalize + embeddings rerank** behind a toggle. AI can only reorder vetted candidates — it cannot invent codes.
* **Next (still local):**
  Flip **“learn when safe”** on for real traffic; promote at 3+ distinct users; automatic demote on collision.
* **Then (AWS at the end):**
  Same logic in Lambda; DynamoDB for synonyms/misses; OpenSearch for vectors; CloudWatch metrics. No behavior change, just shared URL + scale.

## Your immediate next step (super concrete)

Let’s agree a **tiny smoke set** we’ll run after each change (manual is fine):

* Symptoms: `bad breath`, `cough`, `fever`, `sore throat`, `headache`, `nausea`
* Labs: `a1c`, `a1c test`, `tsh`, `ldl`, `cbc`, `vitamin d`
* Conditions: `hypertension`, `high blood pressure`, `diabetes`, `asthma`
* Typos/aliases (we’ll allow later with AI): `halotosis`, `suger test`, `cholestrol`, `bp high`

**Pass criteria (for today’s spine):**

* Patient gets **one** sensible result or a clear **abstain**.
* Practitioner shows **SNOMED/LOINC only**, trimmed for noise.
* No irrelevant “surprises” (e.g., IBS for halitosis, cholesterol for A1C).

If you’re good with this, we keep iterating one tiny step at a time:

1. lock this smoke set as our baseline,
2. add the **embeddings reranker** toggle next (no UI change),
3. measure a quick accuracy lift on that set,
4. only then expand to TS live behind a toggle.

Short version: **we won’t trust “AI will figure it out”**. We’ll **measure**, keep the rails, and introduce AI where it’s safe and proves a lift.


README — Safe Toggles & Quick Checks
Env toggles

USE_RERANK: 0 (off, default) or 1 (on). Reorders vetted candidates only; never invents new codes.

USE_EMBEDDINGS: 0 or 1 (optional; only matters if USE_RERANK=1). When 1, uses an embedding model; else falls back to fuzz.

EMB_MODEL: e.g. all-MiniLM-L6-v2

USE_AUTO_LEARN: 1 (on, default) or 0 (off). When on, the system will learn a new lay phrase only if:

there’s exactly one patient candidate,

its score is ≥ 92, and

the code is on the internal whitelist (e.g., A1c 4548-4, total cholesterol 2093-3, glucose 2339-0, hypertension 38341003, obesity 414916001, diabetes 44054006).