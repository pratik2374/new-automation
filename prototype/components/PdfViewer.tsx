"use client";
import { memo, useCallback, useEffect, useRef, useState } from "react";
import { getPdfjs } from "@/lib/pdfjs";
import { drawTexts, ItemEdit, removePage, replaceInPdf, replaceItems } from "@/lib/edit";
import { PageInfo, readPdf, TItem } from "@/lib/text";

interface Props { bytes: Uint8Array; name: string; onSave: (b: Uint8Array) => void }
type Tool = "view" | "edit" | "text";
// "add" = a new text box placed by clicking; "replace" = editing a text item that already exists in the PDF
type Edit =
  | { id: number; kind: "add"; page: number; fx: number; fy: number; text: string }
  | { id: number; kind: "replace"; page: number; item: TItem; text: string };
const FONT = 11; // pt, size of newly added text

const PageCanvas = memo(function PageCanvas({ doc, index, w, h, scale }: { doc: any; index: number; w: number; h: number; scale: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const wrap = useRef<HTMLDivElement>(null);
  const [vis, setVis] = useState(false);
  useEffect(() => {
    const io = new IntersectionObserver((e) => e[0].isIntersecting && setVis(true), { rootMargin: "800px" });
    if (wrap.current) io.observe(wrap.current);
    return () => io.disconnect();
  }, []);
  useEffect(() => {
    if (!vis) return;
    let task: any;
    (async () => {
      const page = await doc.getPage(index + 1);
      const dpr = window.devicePixelRatio || 1;
      const vp = page.getViewport({ scale: scale * dpr });
      const c = ref.current!;
      c.width = vp.width; c.height = vp.height;
      task = page.render({ canvasContext: c.getContext("2d")!, viewport: vp });
      try { await task.promise; } catch { /* cancelled */ }
    })();
    return () => task?.cancel();
  }, [vis, doc, index, scale]);
  return (
    <div ref={wrap} style={{ width: w * scale, height: h * scale }} className="pagebox">
      <canvas ref={ref} style={{ width: "100%", height: "100%" }} role="img" aria-label={`Page ${index + 1} of the document`} />
    </div>
  );
});

export default function PdfViewer({ bytes, name, onSave }: Props) {
  const [doc, setDoc] = useState<any>(null);
  const [sizes, setSizes] = useState<{ w: number; h: number }[]>([]);
  const [textPages, setTextPages] = useState<PageInfo[]>([]);
  const [zoom, setZoom] = useState(1);
  const [boxW, setBoxW] = useState(700);
  const [tool, setTool] = useState<Tool>("view");
  const [edits, setEdits] = useState<Edit[]>([]);
  const [find, setFind] = useState("");
  const [repl, setRepl] = useState("");
  const [msg, setMsg] = useState("");
  const host = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  useEffect(() => {
    const el = host.current;
    if (!el) return;
    const ro = new ResizeObserver(() => setBoxW(el.clientWidth));
    ro.observe(el);
    setBoxW(el.clientWidth);
    return () => ro.disconnect();
  }, []);

  useEffect(() => {
    let dead = false;
    setEdits([]); setMsg(""); setTextPages([]);
    (async () => {
      const pdfjs = await getPdfjs();
      const d = await pdfjs.getDocument({ data: bytes.slice() }).promise;
      const s: { w: number; h: number }[] = [];
      for (let i = 1; i <= d.numPages; i++) { const vp = (await d.getPage(i)).getViewport({ scale: 1 }); s.push({ w: vp.width, h: vp.height }); }
      if (!dead) { setDoc(d); setSizes(s); }
      const info = await readPdf(bytes); // existing text + positions, used by "Edit Text"
      if (!dead) setTextPages(info.pages);
    })();
    return () => { dead = true; };
  }, [bytes]);

  const scaleFor = (w: number) => Math.max(0.2, ((boxW - 40) / w) * zoom);
  const removeEdit = (id: number) => setEdits((x) => x.filter((y) => y.id !== id));
  const setText = (id: number, text: string) => setEdits((x) => x.map((y) => (y.id === id ? { ...y, text } : y)));

  const addAt = (e: React.MouseEvent<HTMLDivElement>, page: number) => {
    if (tool !== "text" || (e.target as HTMLElement).closest(".editbox")) return;
    const r = e.currentTarget.getBoundingClientRect();
    setEdits((x) => [...x, { id: nextId.current++, kind: "add", page, fx: (e.clientX - r.left) / r.width, fy: (e.clientY - r.top) / r.height, text: "" }]);
  };

  const editItem = (page: number, item: TItem) => {
    setEdits((x) => (x.some((y) => y.kind === "replace" && y.page === page && y.item === item) ? x : [...x, { id: nextId.current++, kind: "replace", page, item, text: item.str }]));
  };

  const pending = edits.filter((e) => (e.kind === "add" ? e.text.trim() : e.text !== e.item.str)).length;

  const save = useCallback(async () => {
    const adds = edits.flatMap((e) => (e.kind === "add" && e.text.trim()
      ? [{ page: e.page, x: e.fx * sizes[e.page].w, y: sizes[e.page].h - e.fy * sizes[e.page].h - FONT * 0.85, text: e.text, size: FONT }] : []));
    const reps: ItemEdit[] = edits.flatMap((e) => (e.kind === "replace" && e.text !== e.item.str
      ? [{ page: e.page, x: e.item.x, y: e.item.y, w: e.item.w, h: e.item.h, old: e.item.str, text: e.text }] : []));
    if (!adds.length && !reps.length) { setMsg("No changes to save"); return; }
    onSave(await drawTexts(await replaceItems(bytes, reps), adds));
    setMsg(`Saved ${adds.length + reps.length} change${adds.length + reps.length > 1 ? "s" : ""}`);
  }, [edits, sizes, bytes, onSave]);

  const doReplace = async () => {
    if (!find) return;
    const esc = find.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    const r = await replaceInPdf(bytes, new RegExp(esc, "g"), repl);
    if (r.count) { onSave(r.bytes); setMsg(`Replaced ${r.count} occurrence${r.count > 1 ? "s" : ""}`); }
    else setMsg("Text not found. Check the spelling and try again");
  };

  const download = () => {
    const url = URL.createObjectURL(new Blob([bytes.slice().buffer], { type: "application/pdf" }));
    const a = document.createElement("a"); a.href = url; a.download = name; a.click(); URL.revokeObjectURL(url);
  };

  const modes: [Tool, string, string][] = [["view", "View", ""], ["edit", "Edit Text", "Click any text in the document to change it"], ["text", "Add Text", "Click anywhere to place a new text box"]];

  return (
    <div className="viewer">
      <div className="toolbar" role="toolbar" aria-label="Document tools">
        <div className="seg" role="group" aria-label="Mode">
          {modes.map(([t, label, tip]) => (
            <button key={t} type="button" title={tip} aria-pressed={tool === t} className={tool === t ? "on" : ""} onClick={() => setTool(t)}>{label}</button>
          ))}
        </div>
        <button type="button" className="ghost accent" onClick={save} disabled={!pending}>Save Edits{pending ? ` (${pending})` : ""}</button>
        <span className="sep" aria-hidden="true" />
        <input aria-label="Find text" name="find" autoComplete="off" spellCheck={false} placeholder="Find text…" value={find} onChange={(e) => setFind(e.target.value)} />
        <input aria-label="Replace with" name="replace" autoComplete="off" spellCheck={false} placeholder="Replace with…" value={repl} onChange={(e) => setRepl(e.target.value)} />
        <button type="button" className="ghost" onClick={doReplace} disabled={!find}>Replace</button>
        <span className="sep" aria-hidden="true" />
        <button type="button" className="ghost" aria-label="Zoom out" onClick={() => setZoom((z) => Math.max(0.4, z - 0.15))}>−</button>
        <span className="zoom num">{Math.round(zoom * 100)}%</span>
        <button type="button" className="ghost" aria-label="Zoom in" onClick={() => setZoom((z) => Math.min(2.5, z + 0.15))}>+</button>
        <button type="button" className="ghost iconbtn" aria-label="Download PDF" title="Download PDF" onClick={download}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M12 3v12" /><path d="m7 11 5 5 5-5" /><path d="M5 20h14" /></svg>
        </button>
      </div>
      {(tool === "edit" || msg) && (
        <div className="statusbar" role="status" aria-live="polite">
          <span>{tool === "edit" ? "Edit Text is on: click any text to change it, then Save Edits." : ""}</span>
          <span className="msg">{msg}</span>
        </div>
      )}
      <div className="pages" ref={host}>
        {!doc && <div className="empty" role="status">Loading document…</div>}
        {doc && sizes.map((s, i) => {
          const sc = scaleFor(s.w);
          const pageEdits = edits.filter((e) => e.page === i);
          const editedItems = new Set(pageEdits.flatMap((e) => (e.kind === "replace" ? [e.item] : [])));
          return (
            <div key={`${name}-${i}`} className="pagewrap" style={{ width: s.w * sc }}>
              <div className="pagehead">
                <span>Page {i + 1} / {sizes.length}</span>
                <button type="button" className="link" aria-label={`Delete page ${i + 1}`} onClick={async () => { if (window.confirm(`Delete page ${i + 1} from ${name}? You can reload the sample to get it back.`)) onSave(await removePage(bytes, i)); }}>Delete Page</button>
              </div>
              <div style={{ position: "relative", cursor: tool === "text" ? "text" : "default" }} onClick={(e) => addAt(e, i)}>
                <PageCanvas doc={doc} index={i} w={s.w} h={s.h} scale={sc} />

                {/* existing text becomes clickable in Edit Text mode */}
                {tool === "edit" && textPages[i]?.items.map((it, k) => !editedItems.has(it) && (
                  <button key={k} type="button" className="hit" aria-label={`Edit text: ${it.str}`}
                    style={{ left: (it.x - 1) * sc, top: (s.h - it.y - it.h * 0.95) * sc, width: (it.w + 2) * sc, height: it.h * 1.25 * sc }}
                    onClick={(e) => { e.stopPropagation(); editItem(i, it); }} />
                ))}

                {pageEdits.map((e) => e.kind === "add" ? (
                  <span key={e.id} className="editbox add" style={{ left: `${e.fx * 100}%`, top: `${e.fy * 100}%` }}>
                    <input autoFocus aria-label="New text" name="newtext" autoComplete="off" spellCheck={false} value={e.text} placeholder="Type here…"
                      style={{ fontSize: FONT * sc, width: Math.max(110, e.text.length * FONT * sc * 0.6 + 16) }}
                      onChange={(ev) => setText(e.id, ev.target.value)} onKeyDown={(ev) => ev.key === "Escape" && removeEdit(e.id)} />
                    <button type="button" className="x" aria-label="Delete this text box" title="Delete" onClick={() => removeEdit(e.id)}>×</button>
                  </span>
                ) : (
                  <span key={e.id} className="editbox rep" style={{ left: (e.item.x - 1) * sc, top: (s.h - e.item.y - e.item.h * 0.95) * sc }}>
                    <input autoFocus aria-label={`Edit text: ${e.item.str}`} name="edittext" autoComplete="off" spellCheck={false} value={e.text}
                      style={{ fontSize: e.item.h * sc, height: e.item.h * 1.25 * sc, width: Math.max(e.item.w + 6, e.text.length * e.item.h * 0.55) * sc }}
                      onChange={(ev) => setText(e.id, ev.target.value)}
                      onKeyDown={(ev) => { if (ev.key === "Escape") removeEdit(e.id); if (ev.key === "Enter") save(); }} />
                    <button type="button" className="x" aria-label="Cancel this edit" title="Cancel edit" onClick={() => removeEdit(e.id)}>×</button>
                  </span>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
