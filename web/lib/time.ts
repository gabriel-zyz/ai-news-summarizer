const rtf = new Intl.RelativeTimeFormat("en", { numeric: "auto", style: "short" });

const STEPS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["minute", 60],
  ["hour", 60 * 60],
  ["day", 60 * 60 * 24],
];

/** "5 min. ago", "3 hr. ago", "yesterday". Null in, empty string out. */
export function timeAgo(iso: string | null, now: number = Date.now()): string {
  if (!iso) return "";
  const seconds = (new Date(iso).getTime() - now) / 1000;
  if (Math.abs(seconds) < 60) return "just now";
  let [unit, size] = STEPS[0];
  for (const step of STEPS) {
    if (Math.abs(seconds) >= step[1]) [unit, size] = step;
  }
  return rtf.format(Math.round(seconds / size), unit);
}

const dateFmt = new Intl.DateTimeFormat("en", { month: "short", day: "numeric", timeZone: "UTC" });

/** Publication time for a headline: relative when precise, a plain date when date-only. */
export function published(iso: string | null, dateOnly: boolean): string {
  if (!iso) return "";
  if (!dateOnly) return timeAgo(iso);
  // A date-only value is local midnight; shift it a few hours so UTC shows the same day.
  return dateFmt.format(new Date(new Date(iso).getTime() + 12 * 3600 * 1000));
}
