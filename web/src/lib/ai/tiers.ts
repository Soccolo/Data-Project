// ─── Tier-based model routing ────────────────────────────────────────
// Each AI call site identifies itself with a `purpose`. The server
// picks the model based on (tier, purpose). Free users get Gemini Flash
// for everything; paid users get Claude on the calls where it matters.

export type Tier = 'free' | 'pro' | 'x';

export type Purpose =
  | 'interview'           // Dara learning who you are — voice matters
  | 'photoAnalysis'       // vision call
  | 'compatibilityFilter' // cheap soft gate before proxy
  | 'proxyTurn'           // Dara-to-Dara matching conversation (HIGH VOLUME)
  | 'score'               // post-match verdict shown to user
  | 'prescreen'           // safety classification on a conflict topic
  | 'intake'              // private conflict intake with own Dara
  | 'mediation'           // Dara-to-Dara conflict mediation (HIGH VOLUME)
  | 'takeaway';           // synthesised takeaways for each partner

export type Provider = 'google' | 'anthropic' | 'deepseek';

export interface ModelChoice {
  provider: Provider;
  model: string;
  // What we tell the user this call is using (helps with debugging + transparency)
  label: string;
}

// Routing table. Edit this to tune the tradeoff between cost and quality.
//
// Heuristics applied:
// - free: all Gemini 2.0 Flash. Cheapest path. Quality is fine for most
//   tasks; matching pairs of free-tier Daras will both speak Flash.
// - pro: Claude Sonnet 4.6 on the personal/sensitive calls the user
//   reads (interview, intake, score, takeaway). Gemini Flash on the
//   volume-heavy shared calls (proxy, mediation) since both partners
//   read the transcript in English regardless of preference.
// - x: All Sonnet. Mediation upgraded to Sonnet for relationship work
//   that benefits from extra nuance.
const ROUTES: Record<Tier, Record<Purpose, ModelChoice>> = {
  free: {
    interview:           { provider: 'google',    model: 'gemini-2.0-flash',         label: 'Gemini Flash' },
    photoAnalysis:       { provider: 'google',    model: 'gemini-2.0-flash',         label: 'Gemini Flash' },
    compatibilityFilter: { provider: 'google',    model: 'gemini-2.0-flash',         label: 'Gemini Flash' },
    proxyTurn:           { provider: 'google',    model: 'gemini-2.0-flash',         label: 'Gemini Flash' },
    score:               { provider: 'google',    model: 'gemini-2.0-flash',         label: 'Gemini Flash' },
    prescreen:           { provider: 'google',    model: 'gemini-2.0-flash',         label: 'Gemini Flash' },
    intake:              { provider: 'google',    model: 'gemini-2.0-flash',         label: 'Gemini Flash' },
    mediation:           { provider: 'google',    model: 'gemini-2.0-flash',         label: 'Gemini Flash' },
    takeaway:            { provider: 'google',    model: 'gemini-2.0-flash',         label: 'Gemini Flash' },
  },
  pro: {
    interview:           { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
    photoAnalysis:       { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
    compatibilityFilter: { provider: 'google',    model: 'gemini-2.0-flash',           label: 'Gemini Flash' },
    proxyTurn:           { provider: 'google',    model: 'gemini-2.0-flash',           label: 'Gemini Flash' },
    score:               { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
    prescreen:           { provider: 'google',    model: 'gemini-2.0-flash',           label: 'Gemini Flash' },
    intake:              { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
    mediation:           { provider: 'google',    model: 'gemini-2.0-flash',           label: 'Gemini Flash' },
    takeaway:            { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
  },
  x: {
    interview:           { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
    photoAnalysis:       { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
    compatibilityFilter: { provider: 'anthropic', model: 'claude-haiku-4-5-20251001',  label: 'Claude Haiku' },
    proxyTurn:           { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
    score:               { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
    prescreen:           { provider: 'anthropic', model: 'claude-haiku-4-5-20251001',  label: 'Claude Haiku' },
    intake:              { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
    mediation:           { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
    takeaway:            { provider: 'anthropic', model: 'claude-sonnet-4-5-20250929', label: 'Claude Sonnet' },
  },
};

export function modelFor(tier: Tier, purpose: Purpose): ModelChoice {
  return ROUTES[tier]?.[purpose] ?? ROUTES.free[purpose];
}

// For two-party calls (Dara-to-Dara proxy, mediation), the "higher" of
// the two users' tiers determines the model. So a pro user matching
// with a free user gets the pro experience.
export function effectiveTier(tierA: Tier, tierB: Tier): Tier {
  const rank = { free: 0, pro: 1, x: 2 } as const;
  return rank[tierA] >= rank[tierB] ? tierA : tierB;
}
