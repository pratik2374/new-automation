export type Kind =
  | "combined_pack" | "audit" | "ebill" | "contract" | "sig_finance" | "sig_installer"
  | "designs" | "site_report" | "salesforce" | "unknown";

export const KIND_LABEL: Record<Kind, string> = {
  combined_pack: "Combined pack (ADI form)",
  audit: "Audit trail",
  ebill: "Electric bill",
  contract: "PPA contract",
  sig_finance: "Finance signature forms",
  sig_installer: "Installer signature forms",
  designs: "Designs (full set)",
  site_report: "Site report",
  salesforce: "Salesforce record (JSON)",
  unknown: "Unrecognised",
};

export const REQUIRED_KINDS: Kind[] = [
  "combined_pack", "audit", "ebill", "contract", "sig_finance", "sig_installer", "designs", "site_report",
];

export interface InFile { id: string; name: string; bytes: Uint8Array; kind: Kind; pages: number }
export interface OutFile { name: string; bytes: Uint8Array; pages: number; note: string }

export type Status = "pass" | "fail" | "warn" | "fixed";
export interface Check { id: string; label: string; status: Status; detail: string }

export interface PortalField { label: string; value: string; flag?: string }
export interface PortalGroup { title: string; fields: PortalField[] }
export interface ArrayRow {
  roof: number; qty: number; rating: string; manufacturer: string; model: string; location: string;
  azimuth: number; tilt: number; tracking: string; access: number; design: number; ideal: number; flag?: string;
}

export interface Result {
  outputs: OutFile[]; checks: Check[]; portal: PortalGroup[]; arrays: ArrayRow[]; log: string[];
  watchouts: string[];
}

export interface Rules {
  financeEmailNew: string;      // replaces the outdated finance-company email on the ADI form
  installerDeptEmail: string;   // replaces the customer-service email on the disclosure
  licenseExpiry: string;
  maxAuditDayGap: number;
}

export const DEFAULT_RULES: Rules = {
  financeEmailNew: "nj.incentives@lightharbor.example",
  installerDeptEmail: "nj.incentives@sunridge-solar.example",
  licenseExpiry: "03/31/2027",
  maxAuditDayGap: 2,
};
