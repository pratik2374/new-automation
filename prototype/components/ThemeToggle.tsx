"use client";
import { useEffect, useState } from "react";

type Theme = "auto" | "light" | "dark";
const KEY = "theme";
const OPTIONS: [Theme, string, string][] = [["auto", "Auto", "Follow system"], ["light", "Light", "Light mode"], ["dark", "Dark", "Dark mode"]];

function apply(t: Theme) {
  const el = document.documentElement;
  if (t === "auto") el.removeAttribute("data-theme"); else el.setAttribute("data-theme", t);
}

export default function ThemeToggle() {
  const [theme, setTheme] = useState<Theme>("auto");
  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY) as Theme | null;
      if (saved === "light" || saved === "dark") setTheme(saved);
    } catch { /* storage unavailable */ }
  }, []);
  const choose = (t: Theme) => {
    setTheme(t); apply(t);
    try { if (t === "auto") localStorage.removeItem(KEY); else localStorage.setItem(KEY, t); } catch { /* ignore */ }
  };
  return (
    <div className="theme" role="group" aria-label="Colour theme">
      {OPTIONS.map(([t, label, title]) => (
        <button key={t} type="button" title={title} aria-pressed={theme === t} className={theme === t ? "on" : ""} onClick={() => choose(t)}>{label}</button>
      ))}
    </div>
  );
}
