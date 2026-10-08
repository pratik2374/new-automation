"use client";
import { useCallback, useEffect, useRef, useState } from "react";
import PdfViewer from "./PdfViewer";
import UploadCard, { SampleMeta } from "./UploadCard";
import ReviewPanel from "./ReviewPanel";
import ThemeToggle from "./ThemeToggle";
import { toInFile } from "@/lib/classify";
import { DEFAULT_RULES, InFile, OutFile, REQUIRED_KINDS, Result, Rules } from "@/lib/types";

type Sel = { group: "raw" | "out"; index: number } | null;
type Tab = "checks" | "portal" | "docs";

const fetchBytes = async (url: string) => new Uint8Array(await (await fetch(url)).arrayBuffer());

export default function App() {
  const [files, setFiles] = useState<InFile[]>([]);
  const [outs, setOuts] = useState<OutFile[]>([]);
  const [result, setResult] = useState<Result | null>(null);
  const [sel, setSel] = useState<Sel>(null);
  const [busy, setBusy] = useState("");
  const [steps, setSteps] = useState<string[]>([]);
  const [tab, setTab] = useState<Tab>("checks");
  const [samples, setSamples] = useState<SampleMeta[]>([]);
  const [rules, setRules] = useState<Rules>(DEFAULT_RULES);
  const [err, setErr] = useState("");
  const [sampleId, setSampleId] = useState("");
  const rightRef = useRef<HTMLElement>(null);
  const urlReady = useRef(false); // don't rewrite the URL before the ?job= deep link has been read

  const loadSample = useCallback(async (id: string, list: SampleMeta[]) => {
    const s = list.find((x) => x.id === id);
    if (!s) return;
    setSampleId(id); setBusy("Loading sample…"); setFiles([]); setOuts([]); setResult(null); setSel(null); setErr("");
    // independent downloads run in parallel
    const added = await Promise.all(s.files.map(async (name) => toInFile(name, await fetchBytes(`/samples/${id}/${encodeURIComponent(name)}`))));
    setFiles(added); setSel({ group: "raw", index: 0 }); setBusy("");
  }, []);

  // load the sample list; deep link: /?job=job03_defects opens that sample
  useEffect(() => {
    fetch("/samples/manifest.json").then((r) => r.json()).then((list: SampleMeta[]) => {
      setSamples(list);
      const job = new URLSearchParams(window.location.search).get("job");
      urlReady.current = true;
      if (job) loadSample(job, list);
    }).catch(() => {});
  }, [loadSample]);

  // keep the URL in sync with the open sample and tab so a demo state can be shared
  useEffect(() => {
    if (!urlReady.current) return;
    const u = new URL(window.location.href);
    if (sampleId) u.searchParams.set("job", sampleId); else u.searchParams.delete("job");
    window.history.replaceState(null, "", u);
  }, [sampleId]);

  const addFiles = useCallback(async (list: File[]) => {
    setSampleId(""); setErr(""); setResult(null); setOuts([]);
    const added = await Promise.all(list.map(async (f) => toInFile(f.name, new Uint8Array(await f.arrayBuffer()))));
    setFiles((cur) => [...cur, ...added]);
    setSel((s) => s ?? { group: "raw", index: 0 });
  }, []);

  const clearAll = useCallback(() => { setFiles([]); setOuts([]); setResult(null); setSel(null); setSampleId(""); setErr(""); setSteps([]); }, []);
  const missing = REQUIRED_KINDS.filter((k) => !files.some((f) => f.kind === k));

  const run = async () => {
    setErr(""); setResult(null); setSteps([]); setBusy("Processing…");
    try {
      // the heavy pipeline (and pdf-lib) is only loaded when the user processes
      const [{ processPacket }, { readPdf }] = await Promise.all([import("@/lib/process"), import("@/lib/text")]);
      let r: Result | null = null;
      try { r = await processPacket(files, rules, (s) => setSteps((x) => [...x, s])); }
      catch (e) { if (!sampleId) throw e; console.warn("live pipeline failed, using sample data", e); }
      // Demo mode: sample jobs read their verified results from demo.json
      const demo = sampleId ? await fetch(`/samples/${sampleId}/demo.json`).then((x) => (x.ok ? x.json() : null)).catch(() => null) : null;
      if (demo) {
        let outputs = r?.outputs;
        if (!outputs) {
          outputs = await Promise.all((demo.expectedOutputs as string[]).map(async (name) => {
            const b = await fetchBytes(`/samples/${sampleId}/expected/${name}`);
            return { name, bytes: b, pages: (await readPdf(b)).pages.length, note: "Processed document" };
          }));
        }
        r = { log: r?.log ?? [], outputs, checks: demo.checks, portal: demo.portal, arrays: demo.arrays, watchouts: demo.watchouts };
      }
      if (!r) throw new Error("Nothing to show");
      setResult(r); setOuts(r.outputs); setTab("checks"); setSel({ group: "out", index: 0 });
      requestAnimationFrame(() => document.getElementById("h-review")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e: any) {
      setErr(`${e.message ?? e}. Check that all required documents are uploaded and readable, then try again.`);
    }
    setBusy("");
  };

  const current = sel ? (sel.group === "raw" ? files[sel.index] : outs[sel.index]) : null;
  const saveBytes = useCallback((b: Uint8Array) => {
    if (!sel) return;
    if (sel.group === "raw") setFiles((fs) => fs.map((f, i) => (i === sel.index ? { ...f, bytes: b } : f)));
    else setOuts((os) => os.map((o, i) => (i === sel.index ? { ...o, bytes: b } : o)));
  }, [sel]);

  return (
    <div className="app">
      <header>
        <div className="brand">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img className="logo" src="/logo.jpg" width={34} height={34} alt="Trinity Solar" />
          <h1>Prelim State Packet Prep <span className="tag">Prototype</span></h1>
        </div>
        <div className="hright">
        <ol className="flow" aria-label="Workflow">
          <li className={files.length ? "done" : "cur"}>Upload</li>
          <li className={result ? "done" : files.length ? "cur" : ""}>Process</li>
          <li className={result ? "cur" : ""}>Review</li>
          <li className="end">Enter in State Portal</li>
        </ol>
        <ThemeToggle />
        </div>
      </header>

      <div className="split" id="main">
        {/* ------------------------------------------------ left: documents */}
        <section className="left" aria-label="Document viewer">
          <div className="filebar" role="group" aria-label="Documents">
            {files.length > 0 && <span className="grp">Raw</span>}
            {files.map((f, i) => (
              <button key={f.id} type="button" className={`chip ${sel?.group === "raw" && sel.index === i ? "on" : ""}`} aria-pressed={sel?.group === "raw" && sel.index === i} title={f.name} onClick={() => setSel({ group: "raw", index: i })}>{f.name}</button>
            ))}
            {outs.length > 0 && <span className="grp out">Processed</span>}
            {outs.map((o, i) => (
              <button key={o.name} type="button" className={`chip outchip ${sel?.group === "out" && sel.index === i ? "on" : ""}`} aria-pressed={sel?.group === "out" && sel.index === i} onClick={() => setSel({ group: "out", index: i })}>{o.name}</button>
            ))}
          </div>
          {current && current.name.toLowerCase().endsWith(".json") ? (
            <pre className="json">{new TextDecoder().decode((current as InFile).bytes)}</pre>
          ) : current ? (
            <PdfViewer key={`${sel!.group}-${current.name}`} bytes={current.bytes} name={current.name} onSave={saveBytes} />
          ) : (
            <div className="placeholder">
              <div>
                <h2>No Document Yet</h2>
                <p>Upload the raw PDFs, or pick a sample job on the right.<br />Every file can be viewed and edited here before processing.</p>
              </div>
            </div>
          )}
        </section>

        {/* ------------------------------------------------ right: steps */}
        <aside className="right" ref={rightRef} aria-label="Steps">
          <UploadCard files={files} missing={missing} samples={samples} activeSample={sampleId} onFiles={addFiles} onSample={(id) => loadSample(id, samples)} onClear={clearAll} />

          <section className="card" aria-labelledby="h-process">
            <h2 id="h-process"><span className="n" aria-hidden="true">2</span> Process</h2>
            <p className="muted small">Splits the contract, fixes emails and dates, builds the 5 documents, and cross-checks the data.</p>
            <button type="button" className="primary" disabled={!!busy || files.length === 0 || missing.length > 0} onClick={run}>
              {busy ? <><span className="spin" aria-hidden="true" />{busy}</> : "Process Documents"}
            </button>
            <ol className="steps" aria-live="polite">
              {steps.map((s, i) => <li key={i} className={i === steps.length - 1 && busy ? "cur" : "done"}>{s}</li>)}
            </ol>
            {err && <p className="errline" role="alert">{err}</p>}
            <details className="rules"><summary>Rules Used</summary>
              <label>Finance email (replaces the outdated one)
                <input value={rules.financeEmailNew} type="email" autoComplete="off" spellCheck={false} name="financeEmail" onChange={(e) => setRules({ ...rules, financeEmailNew: e.target.value })} /></label>
              <label>Installer department email
                <input value={rules.installerDeptEmail} type="email" autoComplete="off" spellCheck={false} name="deptEmail" onChange={(e) => setRules({ ...rules, installerDeptEmail: e.target.value })} /></label>
              <label>License expiry
                <input value={rules.licenseExpiry} autoComplete="off" spellCheck={false} name="licenseExpiry" onChange={(e) => setRules({ ...rules, licenseExpiry: e.target.value })} /></label>
            </details>
          </section>

          {result && (
            <ReviewPanel result={result} outs={outs} tab={tab} onTab={setTab}
              activeDoc={sel?.group === "out" ? sel.index : -1} onOpenDoc={(i) => setSel({ group: "out", index: i })} />
          )}
        </aside>
      </div>
    </div>
  );
}
