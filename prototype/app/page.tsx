"use client";
import dynamic from "next/dynamic";

// pdf.js needs the browser, so the whole app is client-only
const App = dynamic(() => import("@/components/App"), { ssr: false, loading: () => <p style={{ padding: 24 }}>Loading…</p> });

export default function Page() {
  return <App />;
}
