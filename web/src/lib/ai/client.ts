'use client';

// ─── AI client for the browser ───────────────────────────────────────
// The existing Dara code's aiCall() and helpers (aiInterview, aiProxyTurn,
// aiScore, etc.) call a single endpoint /api/llm instead of hitting
// Anthropic/Google directly. The server picks the actual model based on
// the user's tier.

import type { Purpose } from './tiers';

export interface AICallArgs {
  purpose: Purpose;
  systemPrompt: string;
  userText?: string;
  history?: Array<{ role: 'user' | 'assistant'; content: string }>;
  media?: Array<{ base64: string; mediaType: string }>;
  schema?: any;
  partnerTier?: 'free' | 'pro' | 'x'; // for two-party calls
}

export async function callAI(args: AICallArgs): Promise<any> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 90_000);
  try {
    const r = await fetch('/api/llm', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(args),
      signal: ctrl.signal,
    });
    if (!r.ok) {
      const e = await r.json().catch(() => ({ error: r.statusText }));
      throw new Error(e.error || `LLM call failed: ${r.status}`);
    }
    const { text } = await r.json();
    // If a schema was requested, the response should be JSON. Parse loosely.
    if (args.schema) return parseJsonLoose(text);
    return text;
  } finally {
    clearTimeout(timer);
  }
}

// Pulled from the artifact's existing parseJsonLoose
export function parseJsonLoose(text: string): any {
  if (!text) return {};
  let clean = text.trim();
  if (clean.startsWith('```')) clean = clean.replace(/^```(?:json)?\s*/, '').replace(/\s*```$/, '');
  try { return JSON.parse(clean); } catch {}
  const first = clean.indexOf('{');
  const last = clean.lastIndexOf('}');
  if (first >= 0 && last > first) {
    try { return JSON.parse(clean.slice(first, last + 1)); } catch {}
  }
  return {};
}
