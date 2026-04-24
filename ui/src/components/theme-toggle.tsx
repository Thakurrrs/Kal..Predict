"use client";

import React, { useEffect, useState } from "react";

type ThemeName = "executive" | "slate";

const STORAGE_KEY = "kal-predict-theme";

export function ThemeToggle() {
  const [theme, setTheme] = useState<ThemeName>("executive");

  useEffect(() => {
    const saved = window.localStorage.getItem(STORAGE_KEY) as ThemeName | null;
    const resolved: ThemeName = saved === "slate" ? "slate" : "executive";
    setTheme(resolved);
    document.documentElement.dataset.theme = resolved;
  }, []);

  function onChange(next: ThemeName) {
    setTheme(next);
    document.documentElement.dataset.theme = next;
    window.localStorage.setItem(STORAGE_KEY, next);
  }

  return (
    <select
      aria-label="Theme preset"
      className="theme-toggle"
      value={theme}
      onChange={(event) => onChange(event.target.value as ThemeName)}
    >
      <option value="executive">Executive Dark</option>
      <option value="slate">Slate Minimal</option>
    </select>
  );
}
