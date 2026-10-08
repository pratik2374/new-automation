import { PDFDocument, StandardFonts, rgb } from "pdf-lib";
import { readPdf } from "./text";

export interface TextEdit { page: number; x: number; y: number; text: string; size?: number; bold?: boolean }

/** Draw new text on top of existing pages (coordinates in PDF points, origin bottom-left). */
export async function drawTexts(bytes: Uint8Array, edits: TextEdit[]): Promise<Uint8Array> {
  if (!edits.length) return bytes;
  const doc = await PDFDocument.load(bytes.slice());
  const reg = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  const pages = doc.getPages();
  for (const e of edits) {
    pages[e.page]?.drawText(e.text, { x: e.x, y: e.y, size: e.size ?? 9, font: e.bold ? bold : reg, color: rgb(0, 0, 0) });
  }
  return doc.save();
}

/**
 * "Edit" existing text: cover the old text item with a white box and draw the replacement.
 * (pdf-lib cannot rewrite text in place, so this is a visual replace - fine for a prototype.)
 */
export async function replaceInPdf(
  bytes: Uint8Array, matcher: RegExp, replacement: string,
): Promise<{ bytes: Uint8Array; count: number }> {
  const info = await readPdf(bytes);
  const doc = await PDFDocument.load(bytes.slice());
  const reg = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  const pages = doc.getPages();
  let count = 0;
  info.pages.forEach((pi, idx) => {
    for (const it of pi.items) {
      matcher.lastIndex = 0;
      if (!matcher.test(it.str)) continue;
      matcher.lastIndex = 0;
      const next = it.str.replace(matcher, replacement);
      const size = it.h || 9;
      // pick the face whose width is closest to the original text width
      const font = Math.abs(bold.widthOfTextAtSize(it.str, size) - it.w) < Math.abs(reg.widthOfTextAtSize(it.str, size) - it.w) ? bold : reg;
      const pg = pages[idx];
      pg.drawRectangle({ x: it.x - 1, y: it.y - size * 0.25, width: Math.max(it.w, font.widthOfTextAtSize(next, size)) + 2, height: size * 1.2, color: rgb(1, 1, 1) });
      pg.drawText(next, { x: it.x, y: it.y, size, font, color: rgb(0, 0, 0) });
      count++;
    }
  });
  return { bytes: count ? await doc.save() : bytes, count };
}

export interface ItemEdit { page: number; x: number; y: number; w: number; h: number; old: string; text: string }

/** Edit existing text in place: white-out the original text item and draw the new text where it was. */
export async function replaceItems(bytes: Uint8Array, edits: ItemEdit[]): Promise<Uint8Array> {
  if (!edits.length) return bytes;
  const doc = await PDFDocument.load(bytes.slice());
  const reg = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  const pages = doc.getPages();
  for (const e of edits) {
    const size = e.h || 9;
    const font = Math.abs(bold.widthOfTextAtSize(e.old, size) - e.w) < Math.abs(reg.widthOfTextAtSize(e.old, size) - e.w) ? bold : reg;
    const pg = pages[e.page];
    pg.drawRectangle({ x: e.x - 1, y: e.y - size * 0.25, width: Math.max(e.w, font.widthOfTextAtSize(e.text, size)) + 2, height: size * 1.2, color: rgb(1, 1, 1) });
    if (e.text) pg.drawText(e.text, { x: e.x, y: e.y, size, font, color: rgb(0, 0, 0) });
  }
  return doc.save();
}

export async function removePage(bytes: Uint8Array, index: number): Promise<Uint8Array> {
  const doc = await PDFDocument.load(bytes.slice());
  if (doc.getPageCount() > 1) doc.removePage(index);
  return doc.save();
}

export async function assemble(parts: { bytes: Uint8Array; pages: number[] }[]): Promise<Uint8Array> {
  const out = await PDFDocument.create();
  for (const p of parts) {
    if (!p.pages.length) continue;
    const src = await PDFDocument.load(p.bytes.slice());
    const copied = await out.copyPages(src, p.pages);
    copied.forEach((c) => out.addPage(c));
  }
  return out.save();
}

export async function nameClarificationLetter(contractName: string, billName: string, signer: string, company: string): Promise<Uint8Array> {
  const doc = await PDFDocument.create();
  const pg = doc.addPage([612, 792]);
  const reg = await doc.embedFont(StandardFonts.Helvetica);
  const bold = await doc.embedFont(StandardFonts.HelveticaBold);
  const t = (s: string, x: number, y: number, f = reg, size = 11) => pg.drawText(s, { x, y, size, font: f, color: rgb(0, 0, 0) });
  t("Garden State Clean Energy Program", 60, 720, bold, 12);
  t("Administrative Review Team", 60, 704);
  t("100 Example Plaza, Suite 520, Trenton, NJ 08000", 60, 688);
  t("RE: Name Clarification", 60, 650, bold, 12);
  pg.drawLine({ start: { x: 60, y: 644 }, end: { x: 552, y: 644 }, thickness: 1 });
  t("To the Garden State Clean Energy Program,", 60, 610);
  t("Please note the following:", 60, 575);
  t(`${contractName} and ${billName} are the same person; one is her maiden name.`, 60, 545);
  t("Sincerely,", 60, 470);
  t("________________________", 60, 430);
  t(`${signer}, ${company}`, 60, 412, reg, 10);
  t("(DRAFT generated by the prototype - review before signing)", 60, 380, reg, 8);
  return doc.save();
}
