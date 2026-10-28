"use client";

import { useCallback, useEffect, useState, useSyncExternalStore } from "react";

import { OutletCard } from "@/components/outlet-card";
import { timeAgo } from "@/lib/time";
import { REGIONS, type FrontPages, type Region } from "@/lib/types";

type Filter = Region | "ALL";
const FILTER_KEY = "frontpages.region";
const REFRESH_MS = 10 * 60 * 1000;

function readFilter(): Filter {
  try {
    const saved = localStorage.getItem(FILTER_KEY);
    if (saved === "ALL" || REGIONS.some((r) => r.id === saved)) return saved as Filter;
  } catch {
    // storage unavailable (private mode): fall through to the default
  }
  return "ALL";
}

async function fetchFrontPages(): Promise<FrontPages> {
  const res = await fetch("/api/frontpages", { cache: "no-store" });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

function subscribeStorage(onChange: () => void) {
  window.addEventListener("storage", onChange);
  return () => window.removeEventListener("storage", onChange);
}

export default function Home() {
  const [data, setData] = useState<FrontPages | null>(null);
  const [error, setError] = useState<string | null>(null);
  // The saved region is read after hydration ("ALL" on the server); a click overrides it
  // even when storage is unavailable.
  const saved = useSyncExternalStore(subscribeStorage, readFilter, () => "ALL" as Filter);
  const [chosen, setChosen] = useState<Filter | null>(null);
  const filter = chosen ?? saved;

  // Bumped by "Try again" to restart the fetch loop.
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    const refresh = () =>
      fetchFrontPages().then(
        (fresh) => {
          if (!active) return;
          setData(fresh);
          setError(null);
        },
        (e: unknown) => {
          if (active) setError(e instanceof Error ? e.message : String(e));
        },
      );
    refresh();
    const timer = setInterval(refresh, REFRESH_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [attempt]);
  const retry = useCallback(() => setAttempt((n) => n + 1), []);

  const choose = (f: Filter) => {
    setChosen(f);
    try {
      localStorage.setItem(FILTER_KEY, f);
    } catch {
      // not persisted; the filter still applies for this visit
    }
  };

  const updated = data?.outlets.map((o) => o.captured_at).sort().at(-1) ?? null;
  const regions = REGIONS.filter((r) => filter === "ALL" || r.id === filter);

  return (
    <div className="mx-auto w-full max-w-7xl px-4 pb-16 sm:px-6">
      <header className="border-b-2 border-ink pt-8 pb-4 sm:pt-12">
        <div className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2">
          <h1 className="font-serif text-4xl font-bold tracking-tight sm:text-5xl">
            Front Pages <span className="whitespace-nowrap text-accent">今日头条</span>
          </h1>
          <p className="text-sm text-muted">
            {updated ? <>Updated {timeAgo(updated)}</> : "Loading…"}
          </p>
        </div>
        <p className="mt-3 max-w-3xl text-[15px] leading-relaxed text-muted">
          What 16 outlets in Australia, the US, mainland China and Taiwan lead with right now, in
          the order each one&apos;s own homepage shows them.
        </p>
      </header>

      <nav
        aria-label="Region"
        className="sticky top-0 z-10 -mx-4 mb-6 flex gap-2 overflow-x-auto border-b border-rule bg-paper/95 px-4 py-3 backdrop-blur sm:-mx-6 sm:px-6"
      >
        {[{ id: "ALL" as const, name: "All regions", local: "" }, ...REGIONS].map((r) => (
          <button
            key={r.id}
            type="button"
            onClick={() => choose(r.id)}
            aria-pressed={filter === r.id}
            className={`shrink-0 rounded-full px-3.5 py-1.5 text-sm transition-colors ${
              filter === r.id
                ? "bg-ink text-paper"
                : "bg-chip text-ink hover:bg-rule"
            }`}
          >
            {r.name}
            {r.local && <span className="ml-1.5 opacity-60">{r.local}</span>}
          </button>
        ))}
      </nav>

      {error && !data && (
        <div className="rounded-lg border border-rule bg-card p-6 text-sm">
          <p>Could not load the front pages ({error}).</p>
          <button type="button" onClick={retry} className="mt-3 font-medium text-accent underline">
            Try again
          </button>
        </div>
      )}

      {!data && !error && <Skeleton />}

      {data &&
        regions.map((region) => {
          const outlets = data.outlets.filter((o) => o.region === region.id);
          if (outlets.length === 0) return null;
          return (
            <section key={region.id} className="mb-10" aria-labelledby={`region-${region.id}`}>
              <h2
                id={`region-${region.id}`}
                className="mb-4 flex items-baseline gap-2 text-xs font-semibold uppercase tracking-[0.14em] text-muted"
              >
                {region.name}
                <span className="font-normal normal-case tracking-normal">{region.local}</span>
              </h2>
              <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
                {outlets.map((outlet) => (
                  <OutletCard key={outlet.id} outlet={outlet} />
                ))}
              </div>
            </section>
          );
        })}

      <footer className="mt-12 border-t border-rule pt-6 text-xs leading-relaxed text-muted">
        <p>
          Headlines are captured every 6 hours from each outlet&apos;s homepage. Titles and short
          excerpts link to the original articles.
        </p>
        <p className="mt-1">
          <a
            href="https://github.com/gabriel-zyz/ai-news-summarizer"
            className="underline hover:text-ink"
          >
            Source on GitHub
          </a>
        </p>
      </footer>
    </div>
  );
}

function Skeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-hidden>
      {Array.from({ length: 8 }, (_, i) => (
        <div key={i} className="h-72 animate-pulse rounded-lg border border-rule bg-card" />
      ))}
    </div>
  );
}
