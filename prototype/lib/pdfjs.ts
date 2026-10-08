// pdf.js must only be loaded in the browser (dynamic import), worker is copied to /public.
let lib: any = null;
export async function getPdfjs() {
  if (!lib) {
    lib = await import("pdfjs-dist");
    lib.GlobalWorkerOptions.workerSrc = "/pdf.worker.min.mjs";
  }
  return lib;
}
