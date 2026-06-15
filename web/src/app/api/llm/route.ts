import { NextRequest, NextResponse } from 'next/server';
import { supabaseServer } from '@/lib/supabase/server';
import { modelFor, effectiveTier, type Purpose, type Tier } from '@/lib/ai/tiers';
import { callProvider } from '@/lib/ai/providers';

export const runtime = 'edge';
export const maxDuration = 60;

// ─── Request shape ───────────────────────────────────────────────────
// {
//   purpose: 'interview' | 'proxyTurn' | ...
//   systemPrompt: string
//   userText?: string
//   history?: Array<{role: 'user'|'assistant', content: string}>
//   media?: Array<{base64: string, mediaType: string}>   // for vision
//   schema?: object                                       // JSON schema
//   partnerTier?: 'free' | 'pro' | 'x'                    // for two-party calls
// }
//
// Response:
// {
//   text: string,        // raw text or JSON the model produced
//   provider: string,
//   model: string,
//   label: string,
// }

export async function POST(req: NextRequest) {
  // ── Auth check: only logged-in users hit the LLM proxy
  const sb = supabaseServer();
  const { data: { user }, error: authErr } = await sb.auth.getUser();
  if (authErr || !user) return NextResponse.json({ error: 'Not authenticated' }, { status: 401 });

  // Read this user's tier
  const { data: row } = await sb.from('users').select('tier').eq('id', user.id).maybeSingle();
  const myTier: Tier = (row?.tier as Tier) || 'free';

  let body: any;
  try { body = await req.json(); }
  catch { return NextResponse.json({ error: 'Bad JSON' }, { status: 400 }); }

  const purpose = body.purpose as Purpose;
  if (!purpose) return NextResponse.json({ error: 'Missing purpose' }, { status: 400 });

  const partnerTier = (body.partnerTier as Tier) || myTier;
  const tier = (purpose === 'proxyTurn' || purpose === 'mediation') ? effectiveTier(myTier, partnerTier) : myTier;
  const choice = modelFor(tier, purpose);

  try {
    const text = await callProvider(choice, body);
    return NextResponse.json({ text, provider: choice.provider, model: choice.model, label: choice.label });
  } catch (e: any) {
    console.error('[api/llm]', e);
    return NextResponse.json({ error: e.message || 'LLM call failed' }, { status: 502 });
  }
}
