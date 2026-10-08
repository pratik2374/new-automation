# Fictional NJ prelim-state test packets

All names, addresses, companies, account numbers and signatures are invented.
Layouts mimic the document types in the walkthrough videos.

| Job | Scenario |
|---|---|
| job01_clean | 14 panels / 2 arrays. Everything consistent. The ADI finance-signer date is blank in the raw file (the specialist fills it in). |
| job02_three_arrays_name_mismatch | 24 panels / 3 arrays (the state AI lumps these into one). E-bill is a phone photo with a different name (maiden name) so a Name Clarification form is required. |
| job03_defects | Deliberate defects: contract DC (6.15) != design DC (5.74); stale site report (16 modules vs 14); audit date 3 days before ADI signing date; disclosure DocuSign envelope ID differs from the contract; customer date missing on ADI; e-bill photo with smudged account number. |

Each job has:
- `raw/`      files as the specialist downloads them from Box/Salesforce (plus `salesforce_opportunity.json`)
- `expected/` the five finished documents (1_ADI, 2_Contract, 3_Disclosure, 4_EBill, 5_Designs) and `expected_values.json`
              (portal field values, per-array data, and which validation checks should PASS/FAIL)

Regenerate with `python generate_test_data.py`.
