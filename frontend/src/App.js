import React, { useCallback, useMemo, useState, useEffect } from "react";

/** Same-origin API (FastAPI serves the React build) */
const API_BASE = ""; // -> /healthz, /lookup, /api/*

/** Normalize SNOMED options with fallback to technical candidates */
function getSnomedOptionsFromResult(r) {
  const p = Array.isArray(r?.practitioner_options?.snomed)
    ? r.practitioner_options.snomed
    : Array.isArray(r?.practitioner_options)
    ? r.practitioner_options
    : [];

  const norm = (arr) =>
    (arr || [])
      .map(o => ({
        code: String(o.code || o.snomed || o.id || ""),
        display: o.display || o.text || o.term || "",
      }))
      .filter(o => o.code);

  const primary = norm(p);
  const tech = norm(r?.technical?.snomed);

  // Merge by code (keep all: MI, Acute MI, STEMI, NSTEMI, etc.)
  const byCode = new Map(primary.map(o => [o.code, o]));
  for (const t of tech) if (!byCode.has(t.code)) byCode.set(t.code, t);

  return Array.from(byCode.values());
}


export default function App() {
  const [query, setQuery] = useState("");
  const [includeTechnical, setIncludeTechnical] = useState(true); // ON so practitioner options/technical fallback come back
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [activeTab, setActiveTab] = useState("patient");

  const [result, setResult] = useState(null);

  // Preview always holds the **currently chosen** SNOMED code/display
  const [preview, setPreview] = useState(null);

  const [saveStatus, setSaveStatus] = useState("");
  const [saveMessage, setSaveMessage] = useState("");
  const [showToast, setShowToast] = useState(false);
  const [toastMsg, setToastMsg] = useState("");

  const [apiHealth, setApiHealth] = useState(null);
  useEffect(() => {
    fetch(`${API_BASE}/healthz`)
      .then((r) => r.json())
      .then((d) => setApiHealth(d.ok ? "online" : "offline"))
      .catch(() => setApiHealth("offline"));
  }, []);

  const copy = useCallback(async (text) => {
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
      } else {
        const ta = document.createElement("textarea");
        ta.value = text;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand("copy");
        document.body.removeChild(ta);
      }
      setToastMsg("Copied to clipboard");
      setShowToast(true);
      setTimeout(() => setShowToast(false), 2000);
    } catch {
      setToastMsg("Copy failed");
      setShowToast(true);
      setTimeout(() => setShowToast(false), 1500);
    }
  }, []);

  const canSave = useMemo(
    () => !!(result && preview && preview.code && preview.display),
    [result, preview]
  );

  const doLookup = useCallback(async () => {
    const q = (query || "").trim();
    if (!q) {
      setError("Enter a term to search.");
      return;
    }
    setLoading(true);
    setError("");
    setResult(null);
    setPreview(null);
    setSaveStatus("");
    setSaveMessage("");

    try {
      const params = new URLSearchParams({
        q,
        domain: "auto",
        include_technical: String(includeTechnical),
        top_k: "5",
        score_cutoff: "70",
        tech_top_k: "8",
        tech_score_cutoff: "60",
      });
      const res = await fetch(`${API_BASE}/lookup?${params.toString()}`);
      if (!res.ok) throw new Error(`Lookup failed (${res.status})`);
      const data = await res.json();

      const r =
        Array.isArray(data?.results) && data.results.length > 0
          ? data.results[0]
          : data;

      const practitionerOptions =
        (Array.isArray(r?.practitioner_options?.snomed) && r.practitioner_options.snomed) ||
        (Array.isArray(r?.practitioner_options) && r.practitioner_options) ||
        [];

      const techSnomed = data?.technical?.snomed || r?.technical?.snomed || [];
      const techLoinc  = data?.technical?.loinc  || r?.technical?.loinc  || [];

      const normalized = {
        text: r?.text || r?.query || r?.term || q,
        patient_view: r?.patient_view,
        practitioner_view: r?.practitioner_view,
        loinc_code: r?.loinc?.code || r?.loinc_code,
        loinc_display: r?.loinc?.display || r?.loinc_display,
        practitioner_options: practitionerOptions,
        technical: { snomed: techSnomed, loinc: techLoinc },
        snomed_code: r?.snomed,
        codeable_concept: r?.codeable_concept || null,
      };
      setResult(normalized);

      const hasAnyOptions = getSnomedOptionsFromResult(normalized).length > 0;
      setActiveTab(hasAnyOptions ? "practitioner" : "patient");

      // Mirror saved selection if present
      if (normalized.snomed_code) {
        const opts = getSnomedOptionsFromResult(normalized);
        const saved = opts.find(o => String(o.code) === String(normalized.snomed_code));
        setPreview(saved ? { code: saved.code, display: saved.display } : null);
      } else {
        setPreview(null);
      }
    } catch (e) {
      setError((e && e.message) || "Lookup error");
    } finally {
      setLoading(false);
    }
  }, [query, includeTechnical]);

  // Handle change in the SNOMED dropdown — value is the CODE (string)
  const onSelectSnomedCode = useCallback((code) => {
    if (!code) {
      setPreview(null);
      setSaveStatus("");
      setSaveMessage("");
      return;
    }
    const opts = getSnomedOptionsFromResult(result || {});
    const chosen = opts.find(o => String(o.code) === String(code));
    if (chosen) {
      setPreview({ code: String(chosen.code), display: chosen.display || "" });
      setSaveStatus("");
      setSaveMessage("");
    } else {
      setPreview(null);
    }
  }, [result]);

  const saveSelection = useCallback(async () => {
    if (!result || !preview) return;
    setSaveStatus("saving");
    setSaveMessage("");
    try {
      const payload = {
        // Send both legacy and new keys for compatibility
        term: result?.text || query,
        code: String(preview.code),          // legacy expected key
        display: preview.display,            // legacy expected key
        lay_text: result?.text || query,
        snomed_code: String(preview.code),   // explicit keys
        snomed_display: preview.display,
        dry_run: false,
      };
      const res = await fetch(`${API_BASE}/api/commit_selection`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(t || `Commit failed (${res.status})`);
      }
      const data = await res.json();
      if (!data?.ok) throw new Error("Commit failed");

      const lookup = data.result || {};
      const r =
        Array.isArray(lookup?.results) && lookup.results.length > 0
          ? lookup.results[0]
          : lookup;

      const practitionerOptions =
        (Array.isArray(r?.practitioner_options?.snomed) && r.practitioner_options.snomed) ||
        (Array.isArray(r?.practitioner_options) && r.practitioner_options) ||
        [];

      const techSnomed = lookup?.technical?.snomed || r?.technical?.snomed || [];
      const techLoinc  = lookup?.technical?.loinc  || r?.technical?.loinc  || [];

      const normalized = {
        text: r?.text || r?.query || r?.term || query,
        patient_view: r?.patient_view,
        practitioner_view: r?.practitioner_view,
        loinc_code: r?.loinc?.code || r?.loinc_code,
        loinc_display: r?.loinc?.display || r?.loinc_display,
        practitioner_options: practitionerOptions,
        technical: { snomed: techSnomed, loinc: techLoinc },
        snomed_code: r?.snomed,
        codeable_concept: r?.codeable_concept || null,
      };
      setResult(normalized);

      setSaveStatus("saved");
      setSaveMessage("Selection committed.");
      setToastMsg("Selection committed.");
      setShowToast(true);
      setTimeout(() => setShowToast(false), 2000);
    } catch (e) {
      setSaveStatus("error");
      const msg = (e && e.message) || "Commit error";
      setSaveMessage(msg);
      setToastMsg(msg);
      setShowToast(true);
      setTimeout(() => setShowToast(false), 2000);
    }
  }, [preview, query, result]);

  const resetToSaved = useCallback(() => {
    const code = result?.snomed_code ? String(result.snomed_code) : "";
    if (!code) {
      setPreview(null);
    } else {
      const opts = getSnomedOptionsFromResult(result || {});
      const saved = opts.find(o => String(o.code) === code);
      setPreview(saved ? { code: saved.code, display: saved.display } : null);
    }

    setSaveMessage("");
    setShowToast(false);
    setToastMsg(code ? "Reset to saved" : "Cleared preview");
    setTimeout(() => {
      setShowToast(true);
      setTimeout(() => setShowToast(false), 1800);
    }, 0);
  }, [result]);

  const unlearnMapping = useCallback(async () => {
    try {
      const term = result?.text || query;
      if (!term) return;

      const res = await fetch(`${API_BASE}/api/unlearn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ term, keep_aliases: true }),
      });

      const data = await res.json();
      if (!res.ok || !data?.ok) {
        throw new Error((data && (data.detail || data.message)) || `Unlearn failed (${res.status})`);
      }

      setPreview(null);
      setToastMsg("Mapping removed");
      setShowToast(true);
      setTimeout(() => setShowToast(false), 1600);

      doLookup();
    } catch (e) {
      setToastMsg((e && e.message) || "Unlearn failed");
      setShowToast(true);
      setTimeout(() => setShowToast(false), 1600);
    }
  }, [result, query, doLookup]);

  const isLoincOnly = useMemo(() => {
    return !!result?.loinc_code && getSnomedOptionsFromResult(result).length === 0;
  }, [result]);

  const currentSnomedCode = useMemo(
    () => (preview?.code ? String(preview.code) : (result?.snomed_code ? String(result.snomed_code) : "")),
    [preview, result]
  );

  const buildCodeableConcept = useCallback(() => {
    if (result?.codeable_concept) return result.codeable_concept;
    if (preview?.code && preview?.display) {
      return {
        coding: [
          {
            system: "http://snomed.info/sct",
            code: String(preview.code),
            display: preview.display,
          },
        ],
        text: result?.text || query,
      };
    }
    if (result?.snomed_code) {
      const guessDisplay = (result?.practitioner_view || "").split(" (")[0] || "";
      return {
        coding: [
          {
            system: "http://snomed.info/sct",
            code: String(result.snomed_code),
            display: guessDisplay || undefined,
          },
        ],
        text: result?.text || query,
      };
    }
    return null;
  }, [result, preview, query]);

  // Keep preview aligned when a fresh result lands
  useEffect(() => {
    if (!result) return;
    const code = result?.snomed_code ? String(result.snomed_code) : "";
    if (code) {
      const opts = getSnomedOptionsFromResult(result);
      const saved = opts.find(o => String(o.code) === code);
      setPreview(saved ? { code: saved.code, display: saved.display } : null);
    } else {
      setPreview(null);
    }
  }, [result]);

  return (
    <div className="min-h-screen bg-gray-50 text-gray-900" style={{ paddingLeft: 24, paddingRight: 24 }}>
      <style>{`
        button {
          margin-right: 8px;
          margin-top: 8px;
          padding: 8px 12px;
          border-radius: 12px;
          border: 1px solid #d1d5db;
          background: #f8fafc;
          color: #111827;
          transition: background-color 120ms ease, box-shadow 120ms ease, color 120ms ease, border-color 120ms ease;
          cursor: pointer;
        }
        button:hover:not(:disabled) {
          background: #eef2f7;
          box-shadow: 0 1px 2px rgba(0,0,0,.06);
        }
        button:disabled {
          opacity: .55;
          cursor: not-allowed;
        }
        button[data-variant="primary"] {
          background: #111827;
          color: #ffffff;
          border-color: #111827;
        }
        button[data-variant="primary"]:hover:not(:disabled) {
          background: #0f172a;
        }
        .tab-btn {
          padding: 8px 14px;
          border-radius: 999px;
          border: 1px solid #e5e7eb;
          background: #fff;
          margin-right: 8px;
        }
        .tab-btn[aria-selected="true"] {
          background: #111827;
          color: #fff;
          border-color: #111827;
        }
        .toast {
          position: fixed; bottom: 24px; right: 24px; background: #111827; color: #fff; padding: 10px 14px; border-radius: 12px;
          box-shadow: 0 4px 20px rgba(0,0,0,.18);
        }
        .badge { display: inline-block; padding: 2px 8px; border-radius: 999px; border: 1px solid #e5e7eb; background: #fff; font-size: 12px; }
        .mono { font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; font-size: 12px; }
        .card { background: #ffffff; border-radius: 16px; box-shadow: 0 1px 2px rgba(0,0,0,.06); padding: 16px; }
      `}</style>

      <div className="max-w-5xl mx-auto grid gap-6 pl-6 md:pl-12">
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-semibold">Akashic Lookup</h1>
          <div className="flex items-center gap-3">
            <span className="text-sm">API: {apiHealth || "checking…"}</span>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                className="h-4 w-4"
                checked={includeTechnical}
                onChange={(e) => setIncludeTechnical(e.target.checked)}
              />
              <span>include technical</span>
            </label>
          </div>
        </header>

        <div className="bg-white rounded-2xl shadow p-4">
          <div className="flex gap-3">
            <input
              className="flex-1 rounded-xl border border-gray-300 px-3 py-2 focus:outline-none focus:ring"
              placeholder="Enter lay term (e.g., watery eyes, high blood pressure)"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") doLookup();
              }}
            />
            <button
              data-variant="primary"
              className="rounded-xl px-4 py-2"
              onClick={doLookup}
              disabled={loading}
            >
              {loading ? "Searching…" : "Search"}
            </button>
          </div>
          {error && (
            <p className="text-sm text-red-600 mt-2">{error}</p>
          )}
        </div>

        {/* RESULTS */}
        {result && (
          <div className="grid gap-4">
            {/* Tabs */}
            <div className="flex items-center">
              <button
                className="tab-btn"
                aria-selected={activeTab === "patient"}
                onClick={() => setActiveTab("patient")}
              >
                Patient view
              </button>
              <button
                className="tab-btn"
                aria-selected={activeTab === "practitioner"}
                onClick={() => setActiveTab("practitioner")}
              >
                Practitioner view
              </button>
            </div>

            {/* Patient Tab */}
            {activeTab === "patient" && (
              <div className="card">
                <div className="flex items-center gap-3 mb-2">
                  <span className="badge">Lay term</span>
                  <span className="mono">{result?.text || query}</span>
                </div>
                <div className="text-lg">
                  {result?.patient_view || "No patient view available."}
                </div>
                {result?.loinc_code && (
                  <div className="mt-3">
                    <span className="badge mr-2">LOINC</span>
                    <span className="mono">{result.loinc_code}</span>
                    {result?.loinc_display ? (
                      <span className="ml-2">— {result.loinc_display}</span>
                    ) : null}
                  </div>
                )}
              </div>
            )}

            {/* Practitioner Tab */}
            {activeTab === "practitioner" && (
              <div className="card">
                {isLoincOnly ? (
                  <div>
                    <p className="mb-2">This item appears to be lab-only (LOINC).</p>
                    <div className="mt-2">
                      <span className="badge mr-2">LOINC</span>
                      <span className="mono">{result?.loinc_code}</span>
                      {result?.loinc_display ? (
                        <span className="ml-2">— {result.loinc_display}</span>
                      ) : null}
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="mb-3">
                      <label className="block text-sm mb-1">SNOMED selection</label>
                      <select
                        className="w-full border border-gray-300 rounded-xl px-3 py-2"
                        onChange={(e) => onSelectSnomedCode(e.target.value)}
                        value={currentSnomedCode || ""}
                      >
                        <option value="">-- choose a SNOMED --</option>
                        {getSnomedOptionsFromResult(result).map((opt, idx) => (
                          <option key={`${opt.code}-${idx}`} value={String(opt.code)}>
                            {opt.display || String(opt.code)} ({String(opt.code)})
                          </option>
                        ))}
                      </select>
                      <div className="text-xs text-gray-500 mt-1">
                        Saved code: {result?.snomed_code ? String(result.snomed_code) : "none"}
                      </div>
                    </div>

                    <div className="flex flex-wrap items-center">
                      <button
                        data-variant="primary"
                        disabled={!canSave || String(preview?.code) === String(result?.snomed_code)}
                        onClick={saveSelection}
                      >
                        {saveStatus === "saving" ? "Saving…" : "Save selection"}
                      </button>
                      <button onClick={resetToSaved}>Reset to saved</button>
                      <button onClick={unlearnMapping}>Unlearn mapping</button>
                      {saveMessage && (
                        <span className={`ml-2 text-sm ${saveStatus === "error" ? "text-red-600" : "text-green-700"}`}>
                          {saveMessage}
                        </span>
                      )}
                    </div>

                    {/* Practitioner Preview */}
                    <div className="mt-4">
                      <div className="mb-2 font-medium">Practitioner text</div>
                      <div>
                        {result?.practitioner_view || "No practitioner view available."}
                      </div>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* CodeableConcept */}
            <div className="card">
              <div className="flex items-center justify-between mb-2">
                <div className="font-medium">FHIR CodeableConcept</div>
                <div>
                  <button onClick={() => copy(JSON.stringify(buildCodeableConcept(), null, 2))}>Copy JSON</button>
                </div>
              </div>
              <pre className="mono overflow-x-auto whitespace-pre-wrap">
{JSON.stringify(buildCodeableConcept(), null, 2)}
              </pre>
            </div>

            {/* Technical Panel */}
            {includeTechnical && (
              <div className="card">
                <div className="flex items-center justify-between mb-2">
                  <div className="font-medium">Technical matches (debug)</div>
                  <div>
                    <button onClick={() => copy(JSON.stringify(result?.technical || {}, null, 2))}>Copy all</button>
                  </div>
                </div>
                <div className="grid md:grid-cols-2 gap-4">
                  <div>
                    <div className="mb-1">SNOMED candidates</div>
                    <ul className="list-disc pl-6">
                      {(result?.technical?.snomed || []).map((s, i) => (
                        <li key={`snomed-${i}`} className="mb-1">
                          <span className="mono">{s.code}</span> — {s.display}
                          {typeof s.score !== "undefined" && (
                            <span className="text-xs text-gray-500 ml-2">score: {s.score}</span>
                          )}
                          <button className="ml-2" onClick={() => copy(JSON.stringify(s, null, 2))}>Copy</button>
                        </li>
                      ))}
                      {(!result?.technical?.snomed || result.technical.snomed.length === 0) && (
                        <li className="text-sm text-gray-500">none</li>
                      )}
                    </ul>
                  </div>
                  <div>
                    <div className="mb-1">LOINC candidates</div>
                    <ul className="list-disc pl-6">
                      {(result?.technical?.loinc || []).map((l, i) => (
                        <li key={`loinc-${i}`} className="mb-1">
                          <span className="mono">{l.code}</span> — {l.display}
                          {typeof l.score !== "undefined" && (
                            <span className="text-xs text-gray-500 ml-2">score: {l.score}</span>
                          )}
                          <button className="ml-2" onClick={() => copy(JSON.stringify(l, null, 2))}>Copy</button>
                        </li>
                      ))}
                      {(!result?.technical?.loinc || result.technical.loinc.length === 0) && (
                        <li className="text-sm text-gray-500">none</li>
                      )}
                    </ul>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        <footer className="py-8 text-sm text-gray-500">
          <div>Akashic Lookup — React UI</div>
        </footer>
      </div>

      {showToast && <div className="toast">{toastMsg}</div>}
    </div>
  );
}