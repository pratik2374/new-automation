import { readPdf } from "./text";
import { InFile, Kind } from "./types";

/** Work out what a raw file is from its content (not its filename). */
export async function classify(name: string, bytes: Uint8Array): Promise<{ kind: Kind; pages: number }> {
  if (name.toLowerCase().endsWith(".json")) return { kind: "salesforce", pages: 0 };
  let info;
  try {
    info = await readPdf(bytes);
  } catch (e) {
    console.error("classify failed", name, e);
    return { kind: "unknown", pages: 0 };
  }
  const n = info.pages.length;
  const t = info.all;
  let kind: Kind = "unknown";
  if (/RSA - ROOF SUMMARIES/.test(t)) kind = "site_report";
  else if (/PV-1 SITE PLAN/.test(t)) kind = "designs";
  else if (n >= 30 && /SOLAR POWER PURCHASE AGREEMENT/.test(t)) kind = "contract";
  else if (/ADI Registration Certification Form/.test(t) && n <= 10) kind = "combined_pack";
  else if (n <= 2 && /Certificate of Completion/i.test(t) && /Record Tracking/.test(t)) kind = "audit";
  else if (n === 1 && /Account Number:/.test(t) && /Meter Number:/.test(t)) kind = "ebill";
  else if (/Company Digital Signature Authorization Form/.test(t)) kind = "sig_installer";
  else if (/Signature Authorization/.test(t) && /Authorized Signatory/.test(t)) kind = "sig_finance";
  return { kind, pages: n };
}

export async function toInFile(name: string, bytes: Uint8Array): Promise<InFile> {
  const { kind, pages } = await classify(name, bytes);
  return { id: `${name}-${Math.random().toString(36).slice(2, 8)}`, name, bytes, kind, pages };
}
