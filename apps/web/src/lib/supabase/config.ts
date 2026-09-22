export type SupabaseConfig = {
  url: string;
  publishableKey: string;
};

export type CommunityFeatureState = "disabled" | "misconfigured" | "ready";

function rawSupabaseConfig(): SupabaseConfig | null {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL?.trim();
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY?.trim();

  if (!url || !publishableKey) {
    return null;
  }

  try {
    new URL(url);
  } catch {
    return null;
  }

  return { url, publishableKey };
}

export function getCommunityFeatureState(): CommunityFeatureState {
  if (process.env.COMPATFORGE_COMMUNITY_ENABLED?.trim() !== "1") {
    return "disabled";
  }
  return rawSupabaseConfig() ? "ready" : "misconfigured";
}

export function getSupabaseConfig(): SupabaseConfig | null {
  return getCommunityFeatureState() === "ready" ? rawSupabaseConfig() : null;
}
