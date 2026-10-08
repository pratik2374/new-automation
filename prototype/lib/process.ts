import { assemble, drawTexts, nameClarificationLetter, replaceInPdf, TextEdit } from "./edit";
import { fieldValue, m1, PageInfo, PdfInfo, readPdf } from "./text";
import {
  ArrayRow, Check, InFile, Kind, OutFile, PortalGroup, Result, Rules, Status,
} from "./types";

const pick = (files: InFile[], k: Kind) => files.find((f) => f.kind === k);
const num = (s: string) => Number(String(s).replace(/,/g, ""));
const same = (a: number, b: number) => Math.abs(a - b) < 0.006;

function parseDate(s: string): Date | null {
  const m = s.match(/(\d{1,2})[-/](\d{1,2})[-/](\d{2,4})/);
  if (m) { let y = +m[3]; if (y < 100) y += 2000; return new Date(y, +m[1] - 1, +m[2]); }
  const d = new Date(s);
  return isNaN(+d) ? null : d;
}
const longDate = (d: Date) => d.toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" });
const shortDate = (d: Date) => `${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}-${String(d.getFullYear()).slice(2)}`;
const dayGap = (a: Date, b: Date) => Math.round(Math.abs(+a - +b) / 86400000);

const pageIdx = (info: PdfInfo, re: RegExp) => info.pages.map((p, i) => (re.test(p.text) ? i : -1)).filter((i) => i >= 0);

export async function processPacket(files: InFile[], rules: Rules, onStep?: (s: string) => void): Promise<Result> {
  const log: string[] = [];
  const checks: Check[] = [];
  const add = (id: string, label: string, status: Status, detail: string) => checks.push({ id, label, status, detail });
  const step = async (s: string) => { onStep?.(s); await new Promise((r) => setTimeout(r, 350)); };

  const need = (k: Kind) => { const f = pick(files, k); if (!f) throw new Error(`Missing file: ${k}`); return f; };
  const pack = need("combined_pack"), audit = need("audit"), bill = need("ebill"), contract = need("contract");
  const sigF = need("sig_finance"), sigI = need("sig_installer"), designs = need("designs"), site = need("site_report");
  const sf = pick(files, "salesforce");
  const sfData = sf ? JSON.parse(new TextDecoder().decode(sf.bytes)) : null;

  // ---------------------------------------------------------------- read & split
  await step("Reading and classifying documents");
  const [packI, auditI, billI, conI, designI, siteI] = await Promise.all([
    readPdf(pack.bytes), readPdf(audit.bytes), readPdf(bill.bytes), readPdf(contract.bytes), readPdf(designs.bytes), readPdf(site.bytes),
  ]);

  await step("Finding the pages we need (ADI form, contract, disclosure, designs)");
  const adiPages = pageIdx(packI, /ADI Registration Certification Form/);
  const adiP1 = packI.pages[adiPages[0]], adiP2 = packI.pages[adiPages[1]];
  if (!adiP1 || !adiP2) throw new Error("Could not find the 2 ADI form pages in the combined pack");
  const sigPageIdx = pageIdx(conI, /Signature Page - Solar Power Purchase Agreement/)[0] ?? 23;
  const cancelIdx = pageIdx(conI, /NOTICE OF CANCELLATION/)[0];
  const markerIdx = pageIdx(conI, /START OF ADI DISCLOSURE/)[0];
  const certIdx = pageIdx(conI, /Certificate Of Completion/i);
  const discIdx: number[] = [];
  for (let i = markerIdx + 1; i < conI.pages.length && !certIdx.includes(i); i++) discIdx.push(i);
  log.push(`ADI form on pack pages ${adiPages.map((i) => i + 1).join(", ")}`);
  log.push(`Contract: agreement 1-${sigPageIdx + 1}, cancellation p${cancelIdx + 1}, disclosure p${discIdx[0] + 1}-${discIdx[discIdx.length - 1] + 1}, DocuSign certificate p${certIdx[0] + 1}-${certIdx[certIdx.length - 1] + 1}`);

  const keepRe = [/PV-1 SITE PLAN/, /PV-3 ELECTRICAL DIAGRAM/, /SPEC SHEET - INVERTER/];
  const keepDesign = designI.pages.map((p, i) => (keepRe.some((r) => r.test(p.text)) ? i : -1)).filter((i) => i >= 0);

  // ---------------------------------------------------------------- extract fields
  await step("Extracting key fields");
  const adi = {
    first: fieldValue(adiP1, "First Name"), last: fieldValue(adiP1, "Last Name"),
    addr: fieldValue(adiP1, "Installation Address"), city: fieldValue(adiP1, "City", 0),
    state: fieldValue(adiP1, "State", 0), zip: fieldValue(adiP1, "Zip Code", 0), email: fieldValue(adiP1, "Email", 0),
    finEmail: fieldValue(adiP1, "Email", 1), finContact: fieldValue(adiP1, "Contact Person", 0),
    finCompany: fieldValue(adiP1, "Company Name", 0), instCompany: fieldValue(adiP1, "Company Name", 1),
    instContact: fieldValue(adiP1, "Contact Person", 1),
  };
  const c1 = conI.pages[0];
  const con = {
    name: fieldValue(c1, "Customer (Homeowner)"), phone: fieldValue(c1, "Phone"), license: fieldValue(c1, "License"),
    dc: num(m1(c1.text, /System Size \(kW DC\):\s*([\d.]+)/)), env: m1(c1.text, /DocuSign Envelope ID:\s*([0-9A-Fa-f-]+)/),
  };
  const dPage = conI.pages[discIdx[0]];
  const discEnv = m1(dPage.text, /DocuSign Envelope ID:\s*([0-9A-Fa-f-]+)/);
  const discCust = fieldValue(dPage, "Customer Name");
  const auditLast = m1(auditI.all, /Signing Complete\s+(\d+\/\d+\/\d{4})/);
  const bt = billI.all;
  const ebill = {
    acct: m1(bt, /Account Number:\s*(.+)/), meter: m1(bt, /Meter Number:\s*(\S+)/),
    name: m1(bt, /Customer:\s*(.+)/), utility: m1(bt, /Utility:\s*(.+?)(?:\s+Rate class|$)/m),
    rate: m1(bt, /Rate class:\s*(\S+)/),
  };

  // designs
  const planPg = designI.pages.find((p) => /PV-1 SITE PLAN/.test(p.text))!;
  const eqPg = designI.pages.find((p) => /PV-5 EQUIPMENT SCHEDULE/.test(p.text))!;
  const des = {
    modules: num(m1(planPg.text, /TOTAL MODULES:\s*(\d+)/)), dc: num(m1(planPg.text, /TOTAL DC:\s*([\d.]+)/)),
    modMfr: m1(eqPg.text, /MODULES\s+\d+ x (\S+)/), modModel: m1(eqPg.text, /MODULES\s+\d+ x \S+ \((.+?)\)/),
    watts: num(m1(eqPg.text, /MODULES.*?\)\s+(\d+) W/)),
    invQty: num(m1(eqPg.text, /INVERTER\s+(\d+) x/)), invMfr: m1(eqPg.text, /INVERTER\s+\d+ x (\S+)/),
    invModel: m1(eqPg.text, /INVERTER\s+\d+ x \S+ (\S+)/), invAc: num(m1(eqPg.text, /([\d.]+) kW AC/)),
    arrays: [...eqPg.text.matchAll(/ARRAY R(\d+):\s*(\d+) modules\s+AZ (\d+)\s+TILT (\d+)\s+=\s*([\d.]+) kW/g)].map((m) => ({
      roof: +m[1], modules: +m[2], az: +m[3], tilt: +m[4], kw: +m[5],
    })),
  };

  // site report rows
  const sitePg = siteI.pages.find((p) => /RSA - ROOF SUMMARIES/.test(p.text))!;
  const rowRe = /^(\d)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d,]+)\s+([\d,]+)\s*$/;
  const rows = sitePg.text.split("\n").map((l) => l.trim().match(rowRe)).filter(Boolean).map((m: any) => ({
    roof: +m[1], pitch: +m[2], az: +m[3], access: +m[4], tsrf: +m[5], modules: +m[6], kw: +m[7], util: num(m[8]), actual: num(m[9]),
  }));
  const siteMods = rows.reduce((s, r) => s + r.modules, 0);
  const siteKw = rows.reduce((s, r) => s + r.kw, 0);

  // ---------------------------------------------------------------- fixes on the raw files
  await step("Applying fixes (emails, missing dates)");
  let packBytes = pack.bytes;
  const r1 = await replaceInPdf(packBytes, /utility@[\w.-]+/, rules.financeEmailNew);
  packBytes = r1.bytes;
  if (r1.count) add("fix_fin_email", "Finance email on ADI form", "fixed", `Replaced outdated email "${adi.finEmail}" with ${rules.financeEmailNew}`);
  else add("fix_fin_email", "Finance email on ADI form", "pass", `Already ${adi.finEmail}`);

  // missing dates / printed name on ADI page 2
  const dateLabels = adiP2.items.filter((i) => i.str.trim() === "Date:").sort((a, b) => a.x - b.x);
  const valueAt = (page: PageInfo, lbl: string, dx: number, y: number, x: number) =>
    page.items.find((i) => Math.abs(i.y - y) < 2.5 && i.x > x + dx - 8 && i.x < x + dx + 40 && i.str.trim() !== lbl);
  const dVals = dateLabels.map((d) => valueAt(adiP2, "Date:", 45, d.y, d.x)?.str.trim() ?? "");
  const baseDate = parseDate(dVals[1] || "");
  const edits: TextEdit[] = [];
  const filled: string[] = [];
  if (baseDate) {
    if (!dVals[0]) { edits.push({ page: adiPages[1], x: dateLabels[0].x + 45, y: dateLabels[0].y, text: shortDate(baseDate) }); filled.push("finance signer date"); }
    if (!dVals[2]) { edits.push({ page: adiPages[1], x: dateLabels[2].x + 45, y: dateLabels[2].y, text: longDate(baseDate) }); filled.push("customer date"); }
  }
  const pnLabels = adiP2.items.filter((i) => i.str.trim() === "Print Name:").sort((a, b) => a.x - b.x);
  if (pnLabels[0] && !valueAt(adiP2, "Print Name:", 45, pnLabels[0].y, pnLabels[0].x)) {
    edits.push({ page: adiPages[1], x: pnLabels[0].x + 45, y: pnLabels[0].y, text: adi.finContact }); filled.push("finance signer printed name");
  }
  packBytes = await drawTexts(packBytes, edits);
  if (!baseDate) add("dates", "Signature dates on ADI form", "fail", "Installer signing date missing - cannot auto-fill the others");
  else if (filled.length) add("dates", "Signature dates on ADI form", "fixed", `Filled in: ${filled.join(", ")} (from installer date ${dVals[1]})`);
  else add("dates", "Signature dates on ADI form", "pass", "All dates present");

  // customer-service email on disclosure
  const rc = await replaceInPdf(contract.bytes, /customer[\w.]*@[\w.-]+/, rules.installerDeptEmail);
  const conBytes = rc.bytes;
  if (rc.count) add("fix_cust_email", "Installer email on disclosure", "fixed", `Replaced customer-service email with department email ${rules.installerDeptEmail}`);
  else add("fix_cust_email", "Installer email on disclosure", "pass", "Department email already used");

  // ---------------------------------------------------------------- build the documents
  await step("Building the 5 documents");
  const outputs: OutFile[] = [];
  const push = async (name: string, bytes: Uint8Array, note: string) => {
    const info = await readPdf(bytes); outputs.push({ name, bytes, pages: info.pages.length, note });
  };
  await push("1_ADI.pdf", await assemble([{ bytes: packBytes, pages: adiPages }, { bytes: audit.bytes, pages: auditI.pages.map((_, i) => i) }]),
    "ADI form (2 pages) + audit trail. Email and dates fixed.");
  await push("2_Contract.pdf", await assemble([
    { bytes: conBytes, pages: [...Array(sigPageIdx + 1).keys(), cancelIdx] },
    { bytes: conBytes, pages: certIdx },
    { bytes: sigF.bytes, pages: [...Array((await readPdf(sigF.bytes)).pages.length).keys()] },
    { bytes: sigI.bytes, pages: [0] },
  ]), `Agreement pp.1-${sigPageIdx + 1} + cancellation notice (p.${cancelIdx + 1}) + DocuSign certificate + signature pages.`);
  await push("3_Disclosure.pdf", await assemble([
    { bytes: conBytes, pages: discIdx }, { bytes: conBytes, pages: certIdx },
    { bytes: sigF.bytes, pages: [...Array((await readPdf(sigF.bytes)).pages.length).keys()] }, { bytes: sigI.bytes, pages: [0] },
  ]), "Disclosure form pages + DocuSign certificate + signature pages. Department email applied.");
  await push("4_EBill.pdf", bill.bytes, "Electric bill (unchanged).");
  await push("5_Designs.pdf", await assemble([{ bytes: designs.bytes, pages: keepDesign }]), "Site plan, electrical diagram and inverter spec only.");

  // ---------------------------------------------------------------- checks
  await step("Running verification checks");
  const dcVals: [string, number][] = [["Contract", con.dc], ["Designs", des.dc], ["Site report", Number(siteKw.toFixed(3))]];
  if (sfData?.system_size_kw) dcVals.push(["Salesforce", Number(sfData.system_size_kw)]);
  const dcOk = dcVals.every(([, v]) => same(v, dcVals[0][1]));
  add("dc", "DC size matches everywhere", dcOk ? "pass" : "fail", dcVals.map(([k, v]) => `${k} ${v.toFixed(3)} kW`).join(" · "));

  const modVals: [string, number][] = [["Designs", des.modules], ["Equipment schedule", des.arrays.reduce((s, a) => s + a.modules, 0)], ["Site report", siteMods]];
  add("panels", "Panel count matches designs", modVals.every(([, v]) => v === modVals[0][1]) ? "pass" : "fail",
    modVals.map(([k, v]) => `${k}: ${v}`).join(" · ") + (modVals.every(([, v]) => v === modVals[0][1]) ? "" : " - site report may be outdated"));

  const aD = parseDate(auditLast), iD = baseDate;
  if (aD && iD) {
    const gap = dayGap(aD, iD);
    add("audit", "Audit date vs signing date", gap <= rules.maxAuditDayGap ? "pass" : "fail", `Audit ${auditLast}, ADI signed ${dVals[1]} (${gap} day${gap === 1 ? "" : "s"} apart, max ${rules.maxAuditDayGap})`);
  } else add("audit", "Audit date vs signing date", "warn", "Could not read one of the dates");

  add("envelope", "DocuSign envelope ID (contract vs disclosure)", con.env && con.env === discEnv ? "pass" : "fail",
    con.env === discEnv ? `Both end ...${con.env.slice(-4)}` : `Contract ...${con.env.slice(-4)} but disclosure ...${discEnv.slice(-4)} - wrong DocuSign form, request the correct one`);

  const lc = (s: string) => s.toLowerCase().replace(/\s+/g, " ").trim();
  const adiName = `${adi.first} ${adi.last}`;
  add("names", "Customer name matches (ADI / contract / disclosure)", lc(adiName) === lc(con.name) && lc(con.name) === lc(discCust) ? "pass" : "fail",
    `ADI "${adiName}" · Contract "${con.name}" · Disclosure "${discCust}"`);

  const nameMismatch = lc(ebill.name) !== lc(con.name);
  if (nameMismatch) {
    const letter = await nameClarificationLetter(con.name, ebill.name.split(" ").map((w) => w[0] + w.slice(1).toLowerCase()).join(" "), adi.instContact, adi.instCompany);
    await push("6_Name_Clarification.pdf", letter, "Draft name-clarification letter (e-bill name differs). Must be signed and uploaded as an additional document.");
    add("ebill_name", "E-bill name vs contract name", "warn", `Bill "${ebill.name}" vs contract "${con.name}" - name clarification letter drafted (if it's a different person, request a missing-doc note instead)`);
  } else add("ebill_name", "E-bill name vs contract name", "pass", `Both "${con.name}"`);

  const digits = (s: string) => s.replace(/\D/g, "");
  const acctBad = /[#?*]/.test(ebill.acct);
  const sfAcct = sfData?.utility_account_number ? digits(sfData.utility_account_number) : "";
  if (acctBad) add("acct", "Utility account number legible", "fail", `E-bill reads "${ebill.acct}" - digits unreadable, take from Salesforce${sfAcct ? ` (${sfData.utility_account_number})` : ""} or ask the customer`);
  else if (sfAcct && sfAcct !== digits(ebill.acct)) add("acct", "Utility account number matches Salesforce", "fail", `E-bill ${ebill.acct} vs Salesforce ${sfData.utility_account_number}`);
  else add("acct", "Utility account number legible", "pass", ebill.acct);
  if (sfData?.utility_meter_number) add("meter", "Meter number matches Salesforce", sfData.utility_meter_number === ebill.meter ? "pass" : "fail", `E-bill ${ebill.meter} · Salesforce ${sfData.utility_meter_number}`);

  const chatter: string[] = sfData?.chatter ?? [];
  const chatterFlag = chatter.some((c) => /(increased|decreased|change order|on hold)/i.test(c));
  if (sfData) add("chatter", "Chatter notes (DC changes / holds)", chatterFlag ? "warn" : "pass", chatter.join(" | ") || "No notes");
  add("size", "System size under 25 kW DC", des.dc < 25 ? "pass" : "warn", des.dc < 25 ? `${des.dc.toFixed(3)} kW - no extra forms required` : "Over 25 kW - extra forms required");

  // ---------------------------------------------------------------- portal values
  await step("Preparing form-filling sheet");
  const arrays: ArrayRow[] = des.arrays.map((a) => {
    const s = rows.find((r) => r.roof === a.roof);
    const flags: string[] = [];
    if (!s) flags.push("no matching row in site report");
    else {
      if (s.modules !== a.modules) flags.push(`site report says ${s.modules} modules`);
      if (s.az !== a.az) flags.push(`site report azimuth ${s.az}`);
      if (s.pitch !== a.tilt) flags.push(`site report pitch ${s.pitch}`);
    }
    return {
      roof: a.roof, qty: a.modules, rating: (des.watts / 1000).toFixed(3), manufacturer: des.modMfr, model: des.modModel,
      location: "Roof", azimuth: a.az, tilt: a.tilt, tracking: "Fixed", access: s?.access ?? 0, design: s?.util ?? 0, ideal: s?.actual ?? 0,
      flag: flags.join("; ") || undefined,
    };
  });

  const cust = adi, total = sfData?.total_install_cost;
  const portal: PortalGroup[] = [
    { title: "Project and customer", fields: [
      { label: "Project name (Last, First)", value: `${cust.last}, ${cust.first}` },
      { label: "First name", value: cust.first }, { label: "Last name", value: cust.last },
      { label: "Address", value: cust.addr }, { label: "City", value: cust.city }, { label: "State", value: cust.state }, { label: "Zip", value: cust.zip },
      { label: "Phone", value: con.phone }, { label: "Email", value: cust.email },
      { label: "Utility account number", value: acctBad ? (sfData?.utility_account_number ?? "") : ebill.acct, flag: acctBad ? "Unreadable on e-bill" : undefined },
      { label: "Meter number", value: ebill.meter },
    ] },
    { title: "Owner and installer", fields: [
      { label: "Owner (financer)", value: cust.finCompany, flag: "Autofilled in the portal" },
      { label: "Solar installer", value: cust.instCompany }, { label: "Contact person", value: cust.instContact },
      { label: "License number", value: con.license }, { label: "License expiry", value: rules.licenseExpiry },
    ] },
    { title: "Project type (always the same for these jobs)", fields: [
      { label: "Interconnection type", value: "Behind the meter" }, { label: "Market segment", value: "Net metered residential" },
      { label: "Registration type", value: "New registration" }, { label: "Installation type", value: "Rooftop" },
      { label: "Customer type", value: "Residential" }, { label: "Tariff", value: ebill.rate || "Residential" },
      { label: "Electrical company", value: ebill.utility || sfData?.utility_company || "" },
      { label: "Total install cost", value: total != null ? `$${Number(total).toLocaleString()}` : "", flag: total == null ? "Add Salesforce record" : undefined },
    ] },
    { title: "Inverter", fields: [
      { label: "Quantity", value: String(des.invQty) }, { label: "Manufacturer", value: des.invMfr }, { label: "Model", value: des.invModel },
      { label: "AC size", value: `${des.invAc} kW  (state AI tool wants ${Math.round(des.invAc * 1000)} W)` },
      { label: "Peak efficiency", value: "0.97 (always)" }, { label: "Location", value: "Outdoor (placeholder)" },
    ] },
  ];

  const watchouts = checks.filter((c) => c.status === "fail" || c.status === "warn").map((c) => `${c.label}: ${c.detail}`);
  await step("Done");
  return { outputs, checks, portal, arrays, log, watchouts };
}
