/** "nolan_chen" | "nolan.chen" | "nolanChen" → "Nolan Chen" */
export function formatName(login: string): string {
  return login
    .replace(/[_.\-]+/g, " ")
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .split(" ")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1).toLowerCase())
    .join(" ");
}

/** "Nolan Chen" → "NC" */
export function initials(login: string): string {
  const parts = formatName(login).split(" ");
  return parts.length >= 2
    ? (parts[0][0] + parts[1][0]).toUpperCase()
    : parts[0][0].toUpperCase();
}

// ── Obsidian deep-links ──
// Opens the local Obsidian app via its obsidian:// URI scheme. Requires Obsidian
// installed with the vault registered under this name. The vault folder can live
// inside a OneDrive-synced directory, so these links jump straight to the source
// evidence backing every report/stat.
export const OBSIDIAN_VAULT =
  process.env.NEXT_PUBLIC_OBSIDIAN_VAULT || "PM-Vault";

/** Open the whole vault in Obsidian. */
export function obsidianVaultUri(): string {
  return `obsidian://open?vault=${encodeURIComponent(OBSIDIAN_VAULT)}`;
}

/**
 * Jump to a specific note by title. Vault files get a random filename suffix,
 * so we open Obsidian's search on the exact title rather than guess the path —
 * this lands on the right note for every existing report with no backend change.
 */
export function obsidianSearchUri(title: string): string {
  return `obsidian://search?vault=${encodeURIComponent(OBSIDIAN_VAULT)}&query=${encodeURIComponent(`"${title}"`)}`;
}
