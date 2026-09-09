const fallbackPath = "/submissions";
const validationOrigin = "https://compatforge.invalid";

export function safeInternalPath(value: string | null, fallback = fallbackPath) {
  if (!value || !value.startsWith("/")) {
    return fallback;
  }

  try {
    const resolved = new URL(value, validationOrigin);
    if (resolved.origin !== validationOrigin) {
      return fallback;
    }
    return `${resolved.pathname}${resolved.search}${resolved.hash}`;
  } catch {
    return fallback;
  }
}
