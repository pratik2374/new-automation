import { getPdfjs } from "./pdfjs";

export interface TItem { str: string; x: number; y: number; w: number; h: number }
export interface PageInfo { w: number; h: number; items: TItem[]; text: string }
export interface PdfInfo { pages: PageInfo[]; all: string }

function toLines(items: TItem[]): string[] {
  const sorted = [...items].sort((a, b) => b.y - a.y || a.x - b.x);
  const lines: TItem[][] = [];
  for (const it of sorted) {
    const last = lines[lines.length - 1];
    if (last && Math.abs(last[0].y - it.y) < 2.5) last.push(it);
    else lines.push([it]);
  }
  return lines.map((l) => l.sort((a, b) => a.x - b.x).map((i) => i.str).join(" "));
}

/** Read text + positions for every page. Positions are PDF points (origin bottom-left). */
export async function readPdf(bytes: Uint8Array): Promise<PdfInfo> {
  const pdfjs = await getPdfjs();
  const task = pdfjs.getDocument({ data: bytes.slice(), useSystemFonts: true });
  const doc = await task.promise;
  const pages: PageInfo[] = [];
  for (let i = 1; i <= doc.numPages; i++) {
    const p = await doc.getPage(i);
    const vp = p.getViewport({ scale: 1 });
    const tc = await p.getTextContent();
    const items: TItem[] = (tc.items as any[])
      .filter((it) => typeof it.str === "string" && it.str.trim() !== "")
      .map((it) => ({ str: it.str, x: it.transform[4], y: it.transform[5], w: it.width, h: it.height || Math.abs(it.transform[3]) }));
    pages.push({ w: vp.width, h: vp.height, items, text: toLines(items).join("\n") });
  }
  await task.destroy();
  return { pages, all: pages.map((p) => p.text).join("\n") };
}

/** Value printed just under a small field label (label at y+10, value at y, x offset +2). */
export function fieldValue(page: PageInfo, label: string, nth = 0): string {
  const labels = page.items.filter((i) => i.str.trim() === label).sort((a, b) => b.y - a.y || a.x - b.x);
  const l = labels[nth];
  if (!l) return "";
  const c = page.items
    .filter((i) => Math.abs(i.x - (l.x + 2)) < 3.5 && i.y < l.y && l.y - i.y < 14)
    .sort((a, b) => b.y - a.y);
  return c[0]?.str.trim() ?? "";
}

export const m1 = (s: string, re: RegExp) => (s.match(re)?.[1] ?? "").trim();
