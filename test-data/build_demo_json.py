"""Build demo.json (checks / portal values / arrays) for each sample job and copy samples into the prototype.
Run after generate_test_data.py:  python build_demo_json.py
"""
import json, os, shutil
import generate_test_data as g

PROTO = os.path.join(g.HERE, "..", "prototype", "public", "samples")
TITLES = {
    "job01_clean": "Job 1 - Baseline (14 panels, 2 arrays, clean)",
    "job02_three_arrays_name_mismatch": "Job 2 - 3 arrays + e-bill name mismatch",
    "job03_defects": "Job 3 - Deliberate defects (DC, dates, DocuSign, e-bill)",
}


def chk(i, label, status, detail):
    return {"id": i, "label": label, "status": status, "detail": detail}


def demo_for(jid, job):
    g.derive(job)
    cu, s, u = job["customer"], job["site"], job["utility"]
    sr_mod = sum(a["modules"] for a in job["arrays_sitereport"])
    sr_kw = round(sum(a["size_kw"] for a in job["arrays_sitereport"]), 3)
    day = int(job["sign_date"].split("-")[1]); aday = int(job["audit_last_date"].split("/")[1])
    gap = abs(day - aday)
    checks = []
    checks.append(chk("dc", "DC size matches everywhere",
                      "pass" if job["kw_contract"] == job["kw_design"] else "fail",
                      f'Contract {job["kw_contract"]:.3f} kW · Designs {job["kw_design"]:.3f} kW · Site report {sr_kw:.3f} kW · Salesforce {job["kw_contract"]:.3f} kW'))
    ok_p = sr_mod == job["panels_design"]
    checks.append(chk("panels", "Panel count matches designs", "pass" if ok_p else "fail",
                      f'Designs: {job["panels_design"]} · Equipment schedule: {job["panels_design"]} · Site report: {sr_mod}' + ("" if ok_p else " - site report may be outdated")))
    checks.append(chk("audit", "Audit date vs signing date", "pass" if gap <= 2 else "fail",
                      f'Audit {job["audit_last_date"]}, ADI signed {job["sign_date"]} ({gap} day{"" if gap == 1 else "s"} apart, max 2)'))
    if job["envelope_disclosure"]:
        checks.append(chk("envelope", "DocuSign envelope ID (contract vs disclosure)", "fail",
                          f'Contract ...{job["envelope"][-4:]} but disclosure ...{job["envelope_disclosure"][-4:]} - wrong DocuSign form, request the correct one'))
    else:
        checks.append(chk("envelope", "DocuSign envelope ID (contract vs disclosure)", "pass", f'Both end ...{job["envelope"][-4:]}'))
    checks.append(chk("names", "Customer name matches (ADI / contract / disclosure)", "pass",
                      f'ADI "{job["full_name"]}" · Contract "{job["full_name"]}" · Disclosure "{job["full_name"]}"'))
    if job["name_clarification"]:
        checks.append(chk("ebill_name", "E-bill name vs contract name", "warn",
                          f'Bill "{job["ebill_name"]}" vs contract "{job["full_name"]}" - name clarification letter drafted (if it\'s a different person, request a missing-doc note instead)'))
    else:
        checks.append(chk("ebill_name", "E-bill name vs contract name", "pass", f'Both "{job["full_name"]}"'))
    if job["ebill_style"] == "photo_blur":
        checks.append(chk("acct", "Utility account number legible", "fail",
                          f'E-bill reads "70### ##### 9" - digits unreadable, take from Salesforce ({u["acct"]}) or ask the customer'))
    else:
        checks.append(chk("acct", "Utility account number legible", "pass", u["acct"]))
    checks.append(chk("meter", "Meter number matches Salesforce", "pass", f'E-bill {u["meter"]} · Salesforce {u["meter"]}'))
    flag = any(w in " ".join(job["chatter"]).lower() for w in ("increased", "decreased", "change order"))
    checks.append(chk("chatter", "Chatter notes (DC changes / holds)", "warn" if flag else "pass", " | ".join(job["chatter"])))
    checks.append(chk("size", "System size under 25 kW DC", "pass", f'{job["kw_design"]:.3f} kW - no extra forms required'))
    checks.append(chk("fix_fin_email", "Finance email on ADI form", "fixed",
                      f'Replaced outdated email "{g.FINANCE["old_email"]}" with {g.FINANCE["new_email"]}'))
    fixed = ["finance signer date"] + (["customer date"] if job["adi_blank_customer_date"] else []) + ["finance signer printed name"]
    checks.append(chk("dates", "Signature dates on ADI form", "fixed",
                      f'Filled in: {", ".join(fixed)} (from installer date {job["sign_date"]})'))
    checks.append(chk("fix_cust_email", "Installer email on disclosure", "fixed",
                      f'Replaced customer-service email with department email {g.INSTALLER["dept_email"]}'))

    acct_bad = job["ebill_style"] == "photo_blur"
    portal = [
        {"title": "Project and customer", "fields": [
            {"label": "Project name (Last, First)", "value": f'{cu["last"]}, {cu["first"]}'},
            {"label": "First name", "value": cu["first"]}, {"label": "Last name", "value": cu["last"]},
            {"label": "Address", "value": s["addr"]}, {"label": "City", "value": s["city"]},
            {"label": "State", "value": s["state"]}, {"label": "Zip", "value": s["zip"]},
            {"label": "Phone", "value": cu["phone"]}, {"label": "Email", "value": cu["email"]},
            {"label": "Utility account number", "value": u["acct"], **({"flag": "Unreadable on e-bill - taken from Salesforce"} if acct_bad else {})},
            {"label": "Meter number", "value": u["meter"]}]},
        {"title": "Owner and installer", "fields": [
            {"label": "Owner (financer)", "value": g.FINANCE["name"], "flag": "Autofilled in the portal"},
            {"label": "Solar installer", "value": g.INSTALLER["name"]}, {"label": "Contact person", "value": g.INSTALLER["contact"]},
            {"label": "License number", "value": g.INSTALLER["license"]}, {"label": "License expiry", "value": g.INSTALLER["license_exp"]}]},
        {"title": "Project type (always the same for these jobs)", "fields": [
            {"label": "Interconnection type", "value": "Behind the meter"}, {"label": "Market segment", "value": "Net metered residential"},
            {"label": "Registration type", "value": "New registration"}, {"label": "Installation type", "value": "Rooftop"},
            {"label": "Customer type", "value": "Residential"}, {"label": "Tariff", "value": u["tariff"]},
            {"label": "Electrical company", "value": u["name"]}, {"label": "Total install cost", "value": f'${job["price"]:,.0f}'}]},
        {"title": "Inverter", "fields": [
            {"label": "Quantity", "value": "1"}, {"label": "Manufacturer", "value": g.INVERTER["mfr"]}, {"label": "Model", "value": g.INVERTER["model"]},
            {"label": "AC size", "value": f'{g.INVERTER["ac_kw"]} kW  (state AI tool wants {int(g.INVERTER["ac_kw"]*1000)} W)'},
            {"label": "Peak efficiency", "value": "0.97 (always)"}, {"label": "Location", "value": "Outdoor (placeholder)"}]},
    ]
    arrays = []
    for a, sa in zip(job["arrays_design"], job["arrays_sitereport"]):
        flags = [f'site report says {sa["modules"]} modules'] if sa["modules"] != a["modules"] else []
        arrays.append({"roof": a["roof"], "qty": a["modules"], "rating": f'{g.PANEL["watts"]/1000:.3f}', "manufacturer": "NOVASUN",
                       "model": g.PANEL["model"], "location": "Roof", "azimuth": a["az"], "tilt": a["pitch"], "tracking": "Fixed",
                       "access": a["access"], "design": a["util"], "ideal": a["actual"], **({"flag": "; ".join(flags)} if flags else {})})
    watch = [f'{c["label"]}: {c["detail"]}' for c in checks if c["status"] in ("fail", "warn")]
    outputs = ["1_ADI.pdf", "2_Contract.pdf", "3_Disclosure.pdf", "4_EBill.pdf", "5_Designs.pdf"] + (["6_Name_Clarification.pdf"] if job["name_clarification"] else [])
    return {"checks": checks, "portal": portal, "arrays": arrays, "watchouts": watch, "expectedOutputs": outputs}


def main():
    manifest = []
    shutil.rmtree(PROTO, ignore_errors=True)
    for jid, job in g.JOBS.items():
        base = os.path.join(g.OUT, jid)
        dst = os.path.join(PROTO, jid)
        os.makedirs(os.path.join(dst, "expected"))
        files = sorted(os.listdir(os.path.join(base, "raw")))
        for f in files:
            shutil.copy(os.path.join(base, "raw", f), os.path.join(dst, f))
        for f in os.listdir(os.path.join(base, "expected")):
            if f.endswith(".pdf"):
                shutil.copy(os.path.join(base, "expected", f), os.path.join(dst, "expected", f))
        with open(os.path.join(dst, "demo.json"), "w") as fh:
            json.dump(demo_for(jid, job), fh, indent=1)
        manifest.append({"id": jid, "title": TITLES[jid], "files": files})
    with open(os.path.join(PROTO, "manifest.json"), "w") as fh:
        json.dump(manifest, fh, indent=1)
    print("demo data written for", len(manifest), "jobs")


if __name__ == "__main__":
    main()
