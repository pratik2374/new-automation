"use client";
import { memo, useRef, useState } from "react";
import { InFile, KIND_LABEL, Kind } from "@/lib/types";

export interface SampleMeta { id: string; title: string; files: string[] }

const SAMPLE_BLURB: Record<string, string> = {
  job01_clean: "Everything consistent. Shows the happy path.",
  job02_three_arrays_name_mismatch: "3 roofs, e-bill name differs. Drafts a name letter.",
  job03_defects: "Planted errors the checks should catch.",
};

interface Props {
  files: InFile[]; missing: Kind[]; samples: SampleMeta[]; activeSample: string;
  onFiles: (f: File[]) => void; onSample: (id: string) => void; onClear: () => void;
}

function UploadCardImpl({ files, missing, samples, activeSample, onFiles, onSample, onClear }: Props) {
  const input = useRef<HTMLInputElement>(null);
  const [drag, setDrag] = useState(false);
  return (
    <section className="card" aria-labelledby="h-upload">
      <h2 id="h-upload"><span className="n" aria-hidden="true">1</span> Upload Documents</h2>
      <label
        className={`drop ${drag ? "over" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setDrag(true); }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => { e.preventDefault(); setDrag(false); onFiles([...e.dataTransfer.files]); }}
      >
        <strong>Drop raw PDFs here</strong> or click to browse
        <span className="muted small">Optional: Salesforce record as .json</span>
        <input ref={input} type="file" multiple accept=".pdf,.json" className="sr" aria-label="Choose raw PDF files"
          onChange={(e) => { if (e.target.files) onFiles([...e.target.files]); e.target.value = ""; }} />
      </label>

      <div className="samples" role="group" aria-label="Sample jobs">
        <span className="small muted">Or try a sample job</span>
        {samples.map((s) => (
          <button key={s.id} type="button" className={`sample ${activeSample === s.id ? "on" : ""}`} aria-pressed={activeSample === s.id} onClick={() => onSample(s.id)}>
            <b>{s.title}</b>
            <span>{SAMPLE_BLURB[s.id] ?? ""}</span>
          </button>
        ))}
      </div>

      {files.length > 0 && (
        <>
          <ul className="files" aria-label="Uploaded files">
            {files.map((f) => (
              <li key={f.id}>
                <span className={f.kind === "unknown" ? "badge bad" : "badge"}>{KIND_LABEL[f.kind]}</span>
                <span className="fname" title={f.name}>{f.name}</span>
                <span className="muted small num">{f.pages ? `${f.pages} p` : ""}</span>
              </li>
            ))}
          </ul>
          <div className="foot">
            {missing.length > 0
              ? <p className="warnline" role="status">Still needed: {missing.map((k) => KIND_LABEL[k]).join(", ")}.</p>
              : <p className="okline" role="status">All required documents found.</p>}
            <button type="button" className="ghost" onClick={onClear}>Clear All</button>
          </div>
        </>
      )}
    </section>
  );
}

export default memo(UploadCardImpl);
