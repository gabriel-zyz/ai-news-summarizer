// Mirrors the Pydantic models in api/index.py.

export type Region = "AU" | "US" | "CN" | "TW";

export interface Headline {
  rank: number;
  title: string;
  url: string;
  published_at: string | null;
  /** The outlet gave only a date; show it as a date, not as "N hours ago". */
  date_only: boolean;
  excerpt: string | null;
}

export interface Outlet {
  id: string;
  name: string;
  region: Region;
  language: "en" | "zh";
  captured_at: string;
  headlines: Headline[];
}

export interface FrontPages {
  outlets: Outlet[];
}

export const REGIONS: { id: Region; name: string; local: string }[] = [
  { id: "AU", name: "Australia", local: "澳大利亚" },
  { id: "US", name: "United States", local: "美国" },
  { id: "CN", name: "Mainland China", local: "中国大陆" },
  { id: "TW", name: "Taiwan", local: "台湾" },
];
