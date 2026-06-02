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
