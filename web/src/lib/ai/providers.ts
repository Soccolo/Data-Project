// ─── Provider implementations ────────────────────────────────────────
// Each provider takes the resolved model id plus the raw request body and
// returns the model's text output. The route handler picks which one to
// call based on the (tier, purpose) routing in `tiers.ts`.

export interface ProviderRequestBody {
  purpose: string;
  systemPrompt: string;
  userText?: string;
  history?: Array<{ role: 'user' | 'assistant'; content: string }>;
  media?: Array<{ base64: string; mediaType: string }>;
  schema?: any;
  partnerTier?: 'free' | 'pro' | 'x';
}

export async function callProvider(
  choice: { provider: string; model: string },
  body: ProviderRequestBody,
): Promise<string> {
  if (choice.provider === 'anthropic') return callAnthropic(choice.model, body);
  if (choice.provider === 'google')    return callGoogle(choice.model, body);
  if (choice.provider === 'deepseek')  return callDeepSeek(choice.model, body);
  throw new Error(`Unknown provider: ${choice.provider}`);
}

async function callAnthropic(model: string, body: any): Promise<string> {
  const key = process.env.ANTHROPIC_API_KEY;
  if (!key) throw new Error('ANTHROPIC_API_KEY not set');

  // Build messages array. If we have history, use it; otherwise build a
  // first turn (optionally with media for vision).
  let messages: any[];
  if (body.history?.length) {
    messages = body.history;
  } else {
    const content: any[] = [];
    if (body.media?.length) {
      for (const m of body.media.slice(0, 5)) {
        content.push({ type: 'image', source: { type: 'base64', media_type: m.mediaType, data: m.base64 } });
      }
    }
    content.push({ type: 'text', text: body.userText || ' ' });
    messages = [{ role: 'user', content }];
  }

  const r = await fetch('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'x-api-key': key,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({ model, max_tokens: 1024, system: body.systemPrompt, messages }),
  });
  if (!r.ok) throw new Error(`Anthropic ${r.status}: ${await r.text()}`);
  const data = await r.json();
  return data.content?.[0]?.text || '';
}

async function callGoogle(model: string, body: any): Promise<string> {
  const key = process.env.GOOGLE_API_KEY;
  if (!key) throw new Error('GOOGLE_API_KEY not set');

  // Build Gemini contents. We map roles: assistant → 'model'.
  let contents: any[] = [];
  if (body.history?.length) {
    contents = body.history.map((m: any) => ({
      role: m.role === 'assistant' ? 'model' : 'user',
      parts: [{ text: m.content }],
    }));
  } else {
    const parts: any[] = [];
    if (body.media?.length) {
      for (const m of body.media.slice(0, 5)) {
        parts.push({ inlineData: { mimeType: m.mediaType, data: m.base64 } });
      }
    }
    parts.push({ text: body.userText || ' ' });
    contents = [{ role: 'user', parts }];
  }

  const generationConfig: any = { maxOutputTokens: 1024 };
  if (body.schema) {
    generationConfig.responseMimeType = 'application/json';
    generationConfig.responseSchema = body.schema;
  }

  const url = `https://generativelanguage.googleapis.com/v1beta/models/${model}:generateContent?key=${key}`;
  const r = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: body.systemPrompt }] },
      contents,
      generationConfig,
    }),
  });
  if (!r.ok) throw new Error(`Google ${r.status}: ${await r.text()}`);
  const data = await r.json();
  return data.candidates?.[0]?.content?.parts?.[0]?.text || '';
}

async function callDeepSeek(model: string, body: any): Promise<string> {
  const key = process.env.DEEPSEEK_API_KEY;
  if (!key) throw new Error('DEEPSEEK_API_KEY not set');

  // DeepSeek follows OpenAI's chat-completions format.
  const messages: any[] = [{ role: 'system', content: body.systemPrompt }];
  if (body.history?.length) {
    for (const m of body.history) messages.push({ role: m.role, content: m.content });
  } else if (body.userText) {
    messages.push({ role: 'user', content: body.userText });
  }

  const r = await fetch('https://api.deepseek.com/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${key}`,
    },
    body: JSON.stringify({
      model, messages, max_tokens: 1024,
      response_format: body.schema ? { type: 'json_object' } : undefined,
    }),
  });
  if (!r.ok) throw new Error(`DeepSeek ${r.status}: ${await r.text()}`);
  const data = await r.json();
  return data.choices?.[0]?.message?.content || '';
}
