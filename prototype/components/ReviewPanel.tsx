"use client";
import { memo, useState } from "react";
import { OutFile, Result, Status } from "@/lib/types";

const ICON: Record<Status, string> = { pass: "✓", fixed: "↻", warn: "!", fail: "✕" };
const STATUS_TEXT: Record<Status, string> = { pass: "OK", fixed: "Auto-fixed", warn: "Check", fail: "Needs attention" };
const ORDER: Status[] = ["fail", "warn", "fixed", "pass"];
type Tab = "checks" | "portal" | "docs";

function Copy({ value, label }: { value: string; label: string }) {
  const [done, setDone] = useState(false);
  return (
    <button type="button" className="copy" disabled={!value} aria-label={`Copy ${label}`}
      onClick={() => { navigator.clipboard?.writeText(value); setDone(true); setTimeout(() => setDone(false), 1000); }}>
      {done ? "Copied" : "Copy"}
    </button>
  );
}

interface Props { result: Result; outs: OutFile[]; tab: Tab; onTab: (t: Tab) => void; onOpenDoc: (i: number) => void; activeDoc: number }

function ReviewPanelImpl({ result, outs, tab, onTab, onOpenDoc, activeDoc }: Props) {
  const n = (s: Status) => result.checks.filter((c) => c.status === s).length;
  const problems = n("fail");
  const tabs: [Tab, string][] = [["checks", "Checks"], ["portal", "Portal Values"], ["docs", "Documents"]];

  return (
    <section className="card grow" aria-labelledby="h-review">
      <h2 id="h-review"><span className="n" aria-hidden="true">3</span> Review Before Filling the Portal</h2>

      <div className={`banner ${problems ? "bad" : "ok"}`} role="status">
        {problems
          ? <><b>{problems} {problems === 1 ? "item needs" : "items need"} attention</b> before you submit to the state portal.</>
          : <><b>Ready to fill the portal.</b> {n("warn") ? `No blocking issues, but ${n("warn")} ${n("warn") === 1 ? "item needs" : "items need"} a quick look.` : "No blocking issues found."}</>}
      </div>
      <div className="summary" aria-label="Check summary">
        <span className="pill fail">{n("fail")} need attention</span><span className="pill warn">{n("warn")} to check</span>
        <span className="pill fixed">{n("fixed")} auto-fixed</span><span className="pill pass">{n("pass")} OK</span>
      </div>

      <div className="tabs" role="tablist" aria-label="Review sections">
        {tabs.map(([t, label]) => (
          <button key={t} type="button" role="tab" id={`tab-${t}`} aria-selected={tab === t} aria-controls={`panel-${t}`} className={tab === t ? "on" : ""} onClick={() => onTab(t)}>{label}</button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "checks" && (
          <ul className="checks">
            {[...result.checks].sort((a, b) => ORDER.indexOf(a.status) - ORDER.indexOf(b.status)).map((c) => (
              <li key={c.id} className={c.status}>
                <span className="ico" aria-hidden="true">{ICON[c.status]}</span>
                <div>
                  <div className="ctitle">{c.label} <span className="stext">{STATUS_TEXT[c.status]}</span></div>
                  <div className="cdetail">{c.detail}</div>
                </div>
              </li>
            ))}
          </ul>
        )}

        {tab === "portal" && (
          <div className="portal">
            {result.watchouts.length > 0 && (
              <div className="watch"><b>Before you submit</b>
                <ul>{result.watchouts.map((w, i) => <li key={i}>{w}</li>)}</ul></div>
            )}
            {result.portal.map((g) => (
              <div key={g.title} className="pgroup">
                <h3>{g.title}</h3>
                <table>
                  <tbody>{g.fields.map((f) => (
                    <tr key={f.label}>
                      <th scope="row" className="pl">{f.label}</th>
                      <td className="pv" translate="no">{f.value || <i className="muted">Not available</i>}{f.flag && <span className="flag">{f.flag}</span>}</td>
                      <td className="pc"><Copy value={f.value} label={f.label} /></td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
            ))}
            <div className="pgroup">
              <h3>Solar Panel Arrays (One Entry per Roof)</h3>
              <div className="scroll">
                <table className="arr">
                  <thead><tr><th scope="col">Roof</th><th scope="col">Qty</th><th scope="col">Rating kW</th><th scope="col">Azimuth</th><th scope="col">Tilt</th><th scope="col">Access %</th><th scope="col">Design Out</th><th scope="col">Ideal Out</th></tr></thead>
                  <tbody>{result.arrays.map((a) => (
                    <tr key={a.roof} className={a.flag ? "flagrow" : ""}>
                      <th scope="row">R{a.roof}</th><td>{a.qty}</td><td>{a.rating}</td><td>{a.azimuth}</td><td>{a.tilt}</td><td>{a.access}</td><td>{a.design.toLocaleString("en-US")}</td><td>{a.ideal.toLocaleString("en-US")}</td>
                    </tr>
                  ))}</tbody>
                </table>
              </div>
              {result.arrays[0] && (
                <p className="small muted" translate="no">Model <b>{result.arrays[0].model}</b> · Manufacturer <b>{result.arrays[0].manufacturer}</b> · Location Roof · Tracking Fixed · {result.arrays.reduce((s, a) => s + a.qty, 0)} panels in total</p>
              )}
              {result.arrays.filter((a) => a.flag).map((a) => <p key={a.roof} className="warnline">R{a.roof}: {a.flag}</p>)}
            </div>
          </div>
        )}

        {tab === "docs" && (
          <ul className="docs">
            {outs.map((o, i) => (
              <li key={o.name}>
                <button type="button" className={activeDoc === i ? "on" : ""} aria-pressed={activeDoc === i} onClick={() => onOpenDoc(i)}>
                  <b>{o.name}</b> <span className="muted small num">{o.pages}&nbsp;pages</span>
                  <span className="small muted">{o.note}</span>
                </button>
              </li>
            ))}
            <li className="small muted">Select a document to view or edit it on the left, then download it.</li>
          </ul>
        )}
      </div>
    </section>
  );
}

export default memo(ReviewPanelImpl);
