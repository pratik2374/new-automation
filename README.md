# Prelim State Packet Prep

A prototype that prepares a solar installer's **NJ prelim state application packet** for submission to the state portal: upload the raw documents, auto-fix and verify them, and get the exact values to type into the portal.

> **Prototype.** It runs on fictional look-alike documents. Several parts are demo shortcuts (see [Limitations](#limitations)).

## The problem

For every job, a specialist spends roughly 20 minutes before the state portal even opens:

1. Download the contract, e-bill, designs, site report, audit trail and ADI form from Box and Salesforce.
2. Edit them into 5 clean PDFs: split pages (contract pages 1-24 + page 30, disclosure + DocuSign pages), add signature pages, swap outdated emails, fill missing dates.
3. Cross-check names, DC size, panel count, account and meter numbers, and dates across the documents.
4. Type the system details into the portal (customer, inverter, one entry per roof array) and upload the 5 PDFs.

The state's own AI upload tool pre-fills the portal form but gets the hard parts wrong (it lumps all panels into one array, drops account-number digits, pre-fills an outdated license), so the team found it slower than manual entry. This prototype automates the work **before** the portal instead.

## What the prototype does

| Step | What happens |
|---|---|
| **1. Upload** | Drop the raw PDFs (and an optional Salesforce `.json`). Files are recognised by their content, not their filenames. |
| **2. Process** | Finds the ADI form pages, splits the 50-page contract, swaps emails, fills missing signature dates, builds the 5 documents, and drafts a name-clarification letter when the e-bill name differs. |
| **3. Review** | **Checks** (DC size, panel count, audit date, DocuSign ID, names, account/meter numbers, Chatter notes), **Portal values** with copy buttons plus a per-roof arrays table, and the **processed documents**. |

The left side is a PDF viewer with **Edit Text** (click existing text and change it in place), **Add Text** (a new text box, with a × to remove it), find and replace, delete page, zoom and download. There is a Light / Dark / Auto theme toggle.

## Quick start

Requires Node 20+ (tested on 22) and, for the test data, Python 3.

```bash
cd prototype
npm install
npm run dev -- -p 3100        # open http://localhost:3100
```

Pick a sample job in the app, or deep-link straight to one:

- `http://localhost:3100/?job=job01_clean`
- `http://localhost:3100/?job=job02_three_arrays_name_mismatch`
- `http://localhost:3100/?job=job03_defects`

Everything runs in the browser (no backend): [pdf.js](https://mozilla.github.io/pdf.js/) reads and renders the PDFs and [pdf-lib](https://pdf-lib.js.org/) splits, merges and edits them.

## Sample jobs

All people, addresses, companies, account numbers and signatures are **invented**.

| Job | Scenario | Expected result |
|---|---|---|
| `job01_clean` | 14 panels, 2 arrays, everything consistent | 0 items need attention, 3 auto-fixed |
| `job02_three_arrays_name_mismatch` | 3 arrays; the e-bill is a phone photo with a different name | Name-clarification letter drafted |
| `job03_defects` | Planted errors | 5 items need attention: DC size mismatch, stale site report, audit date off, wrong DocuSign ID, unreadable account number |

**Demo mode:** sample jobs read their checks, portal values and array table from `prototype/public/samples/<job>/demo.json`, so the demo is deterministic. The PDFs are still built live by the pipeline; if that fails, the finished PDFs in `samples/<job>/expected/` are shown instead. Files you upload yourself always go through the real pipeline.

## Repository layout

```
prototype/                 Next.js app
  app/                     layout, page, global styles (glass UI, light/dark theme)
  components/              App, PdfViewer, UploadCard, ReviewPanel, ThemeToggle
  lib/process.ts           the pipeline: split, fix, extract, check, build
  lib/edit.ts              PDF edits (assemble pages, replace text, add text)
  lib/classify.ts          recognise document types from their content
  public/samples/          3 sample jobs + demo.json per job
test-data/
  generate_test_data.py    builds the fictional packets (raw/ and expected/ per job)
  build_demo_json.py       builds demo.json and copies samples into the app
```

Regenerate the test data after editing the generator:

```bash
cd test-data
pip install reportlab pypdf pillow
python generate_test_data.py
python build_demo_json.py
```

## Limitations

- **No OCR.** The sample e-bills carry an invisible text layer standing in for OCR output. Real photographed bills need OCR.
- **Text edits are visual.** pdf-lib cannot rewrite text objects, so an edit whites out the original text and draws the new text on top. The old words still exist underneath, so this is fine for a demo but not for an official record.
- **Rules are tuned to the sample documents** (page markers, emails, license expiry). Real packets will need those adjusted.
- **No portal automation.** The prototype stops right before the state portal: it prepares the documents and values, and a person still enters them.

## Privacy

The video screenshots used to design the sample documents contain real customer data and are deliberately **not** in this repository (`frames/` and `sheets/` are git-ignored).
