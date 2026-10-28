"use client";

import { useState } from "react";

import { published, timeAgo } from "@/lib/time";
import type { Headline, Outlet } from "@/lib/types";

const COLLAPSED = 5;

// Simplified for mainland outlets, traditional for Taiwan: picks the right CJK glyphs.
const LANG: Record<Outlet["region"], string> = { AU: "en", US: "en", CN: "zh-Hans", TW: "zh-Hant" };

export function OutletCard({ outlet }: { outlet: Outlet }) {
  const [expanded, setExpanded] = useState(false);
  const [lead, ...rest] = outlet.headlines;
  const shown = expanded ? rest : rest.slice(0, COLLAPSED - 1);
  const lang = LANG[outlet.region];

  return (
    <article className="flex flex-col rounded-lg border border-rule bg-card">
      <header className="flex items-baseline justify-between gap-3 border-b border-rule px-4 py-3">
        <h3 className="font-semibold">{outlet.name}</h3>
        <span className="shrink-0 text-xs text-muted">{timeAgo(outlet.captured_at)}</span>
      </header>

      {lead && <Lead headline={lead} lang={lang} />}

      <ol className="flex-1 divide-y divide-rule px-4">
        {shown.map((h) => (
          <li key={h.rank} className="flex gap-3 py-2.5">
            <span className="w-4 shrink-0 pt-0.5 text-right font-mono text-xs text-muted">
              {h.rank}
            </span>
            <a
              href={h.url}
              target="_blank"
              rel="noopener noreferrer"
              lang={lang}
              className="text-[15px] leading-snug hover:text-accent"
            >
              {h.title}
            </a>
          </li>
        ))}
      </ol>

      {rest.length > COLLAPSED - 1 && (
        <button
          type="button"
          onClick={() => setExpanded((v) => !v)}
          className="border-t border-rule px-4 py-2.5 text-left text-sm text-muted hover:text-ink"
        >
          {expanded ? "Show fewer" : `Show all ${outlet.headlines.length}`}
        </button>
      )}
    </article>
  );
}

function Lead({ headline, lang }: { headline: Headline; lang: string }) {
  return (
    <div className="border-b border-rule px-4 pt-3 pb-4">
      <a
        href={headline.url}
        target="_blank"
        rel="noopener noreferrer"
        lang={lang}
        className="font-serif text-xl leading-snug font-semibold hover:text-accent"
      >
        {headline.title}
      </a>
      {headline.excerpt && (
        <p lang={lang} className="mt-2 line-clamp-3 text-sm leading-relaxed text-muted">
          {headline.excerpt}
        </p>
      )}
      {headline.published_at && (
        <p className="mt-2 text-xs text-muted">
          {published(headline.published_at, headline.date_only)}
        </p>
      )}
    </div>
  );
}
