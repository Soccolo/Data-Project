'use client';

// ─── window.storage compatibility layer ──────────────────────────────
// The existing Dara artifact code uses window.storage.{get,set,list,delete}
// with key patterns like 'dara-user-{id}', 'dara-photos-{id}-3', etc.
// To avoid rewriting 4000+ lines of React, we keep the same surface and
// translate every call to a Supabase query or storage operation behind
// the scenes.
//
// IMPORTANT design choice: the artifact's window.storage was a flat
// key-value store. We're mapping it onto a proper schema. The mapping
// for each key prefix is defined in the switch statements below.

import { supabaseBrowser } from '@/lib/supabase/client';

type StoredValue = string;

interface StorageResult<T> {
  key: string;
  value: T;
  shared?: boolean;
}

// ─── Key parsers ─────────────────────────────────────────────────────
// We pattern-match on the key prefix to figure out where the data lives.
//
// Artifact keys we need to handle:
//   dara-session                            → cached locally (current user id)
//   dara-api-config                         → ignored (server-side now)
//   dara-users-index                        → derived from public.users table
//   dara-username-{username}                → derived
//   dara-user-{id}                          → public.users row
//   dara-state-{id}                         → public.user_state row
//   dara-photos-{id}-count                  → count from public.photos
//   dara-photos-{id}-{n}                    → photos[n] for user id
//   dara-cs-{sessionId}                     → public.conflict_sessions row
//   dara-cs-index-{userId}                  → derived from conflict_sessions

const RE_USER     = /^dara-user-(.+)$/;
const RE_USERNAME = /^dara-username-(.+)$/;
const RE_STATE    = /^dara-state-(.+)$/;
const RE_PHOTO    = /^dara-photos-([^-]+)-(\d+|count)$/;
const RE_CS       = /^dara-cs-([^-]+)$/;
const RE_CS_INDEX = /^dara-cs-index-(.+)$/;

// ─── In-memory caches for the active session ─────────────────────────
// These avoid hitting Supabase for the same key dozens of times per second
// (the React code is chatty). They invalidate on set/delete.
const cache = new Map<string, string>();

function setCache(key: string, value: string) { cache.set(key, value); }
function clearCache(key: string) { cache.delete(key); }
function clearCacheStartingWith(prefix: string) {
  for (const k of cache.keys()) if (k.startsWith(prefix)) cache.delete(k);
}

// ─── Photo upload helper ─────────────────────────────────────────────
// The artifact storage held photos as data URLs (`data:image/jpeg;base64,...`)
// inline. In production they live in Supabase Storage. We convert on write.
async function uploadDataUrl(userId: string, dataUrl: string): Promise<{ path: string; mediaType: string }> {
  const sb = supabaseBrowser();
  const m = /^data:([^;]+);base64,(.+)$/.exec(dataUrl);
  if (!m) throw new Error('Not a base64 data URL');
  const mediaType = m[1];
  const bytes = Uint8Array.from(atob(m[2]), c => c.charCodeAt(0));
  const ext = mediaType.split('/')[1] || 'jpg';
  const path = `${userId}/${crypto.randomUUID()}.${ext}`;
  const { error } = await sb.storage.from('dara-photos').upload(path, bytes, { contentType: mediaType, upsert: true });
  if (error) throw error;
  return { path, mediaType };
}

async function signedUrlFor(path: string): Promise<string> {
  const sb = supabaseBrowser();
  const { data, error } = await sb.storage.from('dara-photos').createSignedUrl(path, 3600);
  if (error || !data) throw error || new Error('No signed URL');
  return data.signedUrl;
}

// ─── get ─────────────────────────────────────────────────────────────
async function get(key: string, _shared = false): Promise<StorageResult<string> | null> {
  if (cache.has(key)) return { key, value: cache.get(key)! };
  const sb = supabaseBrowser();

  // dara-session: stored only in localStorage on the client, since it's just
  // the active user id (Supabase's own session handles auth tokens).
  if (key === 'dara-session') {
    const v = typeof window !== 'undefined' ? localStorage.getItem(key) : null;
    return v ? { key, value: v } : null;
  }

  // Ignored keys
  if (key === 'dara-api-config') return null;
  if (key === 'dara-users-index') {
    // Return an array of all user IDs (used to find demo + real candidates)
    const { data } = await sb.from('users').select('id');
    const ids = (data || []).map((r: any) => r.id);
    const val = JSON.stringify(ids);
    setCache(key, val);
    return { key, value: val };
  }

  let m = key.match(RE_USERNAME);
  if (m) {
    const username = m[1];
    const { data } = await sb.from('users').select('id').ilike('username', username).maybeSingle();
    if (!data) return null;
    setCache(key, data.id);
    return { key, value: data.id };
  }

  m = key.match(RE_USER);
  if (m) {
    const id = m[1];
    const { data } = await sb.from('users').select('*').eq('id', id).maybeSingle();
    if (!data) return null;
    // Reshape to match the artifact's expected meta object
    const meta = {
      id: data.id,
      auth: { username: data.username, email: data.email, passHash: null },
      basics: data.basics || {},
      profile: data.profile || {},
      tier: data.tier,
      kind: data.kind,
    };
    const val = JSON.stringify(meta);
    setCache(key, val);
    return { key, value: val };
  }

  m = key.match(RE_STATE);
  if (m) {
    const id = m[1];
    const { data } = await sb.from('user_state').select('*').eq('user_id', id).maybeSingle();
    const stateData = data
      ? { passes: data.passed_ids || [], meets: [], dailyCount: data.daily_count }
      : { passes: [], meets: [], dailyCount: { date: null, count: 0 } };
    // Pull this user's meets (where they're either side)
    const { data: meets } = await sb.from('meets').select('*').or(`proposer_id.eq.${id},recipient_id.eq.${id}`);
    stateData.meets = (meets || []).map(reshapeMeet);
    const val = JSON.stringify(stateData);
    setCache(key, val);
    return { key, value: val };
  }

  m = key.match(RE_PHOTO);
  if (m) {
    const userId = m[1];
    const part = m[2];
    const { data: photos } = await sb.from('photos').select('*').eq('user_id', userId).order('position');
    if (part === 'count') {
      const val = String(photos?.length || 0);
      setCache(key, val);
      return { key, value: val };
    }
    const idx = parseInt(part, 10);
    const photo = photos?.[idx];
    if (!photo) return null;
    // Build a signed URL and return as the data shape the React code expects
    const signedUrl = await signedUrlFor(photo.storage_path);
    const photoObj = { dataUrl: signedUrl, mediaType: photo.media_type, base64: '' };
    const val = JSON.stringify(photoObj);
    setCache(key, val);
    return { key, value: val };
  }

  m = key.match(RE_CS);
  if (m) {
    const sid = m[1];
    const { data } = await sb.from('conflict_sessions').select('*').eq('id', sid).maybeSingle();
    if (!data) return null;
    const val = JSON.stringify(reshapeConflictSession(data));
    setCache(key, val);
    return { key, value: val };
  }

  m = key.match(RE_CS_INDEX);
  if (m) {
    const userId = m[1];
    const { data } = await sb.from('conflict_sessions').select('id').or(`inviter_id.eq.${userId},invitee_id.eq.${userId}`);
    const ids = (data || []).map((r: any) => r.id);
    const val = JSON.stringify(ids);
    setCache(key, val);
    return { key, value: val };
  }

  console.warn('[storage.get] unhandled key', key);
  return null;
}

// ─── set ─────────────────────────────────────────────────────────────
async function set(key: string, value: string, _shared = false): Promise<StorageResult<string> | null> {
  const sb = supabaseBrowser();

  if (key === 'dara-session') {
    if (typeof window !== 'undefined') localStorage.setItem(key, value);
    setCache(key, value);
    return { key, value };
  }
  if (key === 'dara-api-config') return { key, value }; // no-op

  let m = key.match(RE_USERNAME);
  if (m) {
    // No-op: username uniqueness is enforced by the users table directly
    setCache(key, value);
    return { key, value };
  }

  m = key.match(RE_USER);
  if (m) {
    const id = m[1];
    const meta = JSON.parse(value);
    const row = {
      id,
      username: meta.auth?.username || meta.basics?.name || 'user',
      email: meta.auth?.email || '',
      basics: meta.basics || {},
      profile: meta.profile || {},
      tier: meta.tier || 'free',
      kind: meta.kind || 'dating',
    };
    const { error } = await sb.from('users').upsert(row, { onConflict: 'id' });
    if (error) { console.error('[storage.set user]', error); return null; }
    setCache(key, value);
    return { key, value };
  }

  m = key.match(RE_STATE);
  if (m) {
    const id = m[1];
    const parsed = JSON.parse(value);
    const { error } = await sb.from('user_state').upsert({
      user_id: id,
      passed_ids: parsed.passes || [],
      daily_count: parsed.dailyCount || { date: null, count: 0 },
    }, { onConflict: 'user_id' });
    if (error) { console.error('[storage.set state]', error); return null; }
    // Meets are written via a separate path (the React code touches state.meets
    // when meets change; we sync those rows here).
    await syncMeetsFromStateBlob(id, parsed.meets || []);
    setCache(key, value);
    return { key, value };
  }

  m = key.match(RE_PHOTO);
  if (m) {
    const userId = m[1];
    const part = m[2];
    if (part === 'count') {
      // Trust the count; nothing to do — photo rows are authoritative
      setCache(key, value);
      return { key, value };
    }
    const idx = parseInt(part, 10);
    const photo = JSON.parse(value);
    // If the value is already a signed URL (i.e. we just round-tripped it from get),
    // don't re-upload — that would create duplicates.
    if (!photo.dataUrl?.startsWith('data:')) {
      setCache(key, value);
      return { key, value };
    }
    try {
      const { path, mediaType } = await uploadDataUrl(userId, photo.dataUrl);
      const { error } = await sb.from('photos').insert({
        user_id: userId, storage_path: path, position: idx, media_type: mediaType,
      });
      if (error) { console.error('[storage.set photo]', error); return null; }
      clearCacheStartingWith(`dara-photos-${userId}`);
      return { key, value };
    } catch (e) { console.error('[storage.set photo upload]', e); return null; }
  }

  m = key.match(RE_CS);
  if (m) {
    const sid = m[1];
    const cs = JSON.parse(value);
    const row = {
      id: sid,
      inviter_id: cs.inviterId, inviter_username: cs.inviterUsername, inviter_name: cs.inviterName,
      invitee_id: cs.inviteeId, invitee_username: cs.inviteeUsername, invitee_name: cs.inviteeName,
      topic: cs.topic, status: cs.status, safety_reason: cs.safetyReason,
      intake: cs.intake, mediation: cs.mediation, takeaways: cs.takeaways,
    };
    const { error } = await sb.from('conflict_sessions').upsert(row, { onConflict: 'id' });
    if (error) { console.error('[storage.set cs]', error); return null; }
    setCache(key, value);
    return { key, value };
  }

  m = key.match(RE_CS_INDEX);
  if (m) {
    // No-op: the conflict_sessions table itself is the source of truth
    setCache(key, value);
    return { key, value };
  }

  console.warn('[storage.set] unhandled key', key);
  return null;
}

// ─── delete / list (rarely used by Dara but needed for compat) ───────
async function del(key: string, shared = false): Promise<StorageResult<boolean> | null> {
  clearCache(key);
  // Most artifact deletes are conceptual (passes, meets). We don't expose a
  // generic delete to RLS — handle on a per-table basis as needed.
  return { key, value: true, shared };
}
async function list(prefix = '', shared = false): Promise<{ keys: string[]; prefix: string; shared: boolean }> {
  // Used only for debug. Real listing happens via direct table queries.
  return { keys: [], prefix, shared };
}

// ─── Reshape helpers ─────────────────────────────────────────────────
function reshapeMeet(r: any) {
  return {
    id: r.id,
    proposerId: r.proposer_id, recipientId: r.recipient_id,
    proposerName: r.proposer_name, recipientName: r.recipient_name,
    time: r.time_str, place: r.place, message: r.message,
    status: r.status,
  };
}
function reshapeConflictSession(r: any) {
  return {
    id: r.id,
    inviterId: r.inviter_id, inviterUsername: r.inviter_username, inviterName: r.inviter_name,
    inviteeId: r.invitee_id, inviteeUsername: r.invitee_username, inviteeName: r.invitee_name,
    topic: r.topic, status: r.status, safetyReason: r.safety_reason,
    created: new Date(r.created_at).getTime(),
    updated: new Date(r.updated_at).getTime(),
    intake: r.intake, mediation: r.mediation, takeaways: r.takeaways,
  };
}

// When the React app writes a state blob with meets, sync each meet to its row.
// This is N+1ish but the React code doesn't call this often.
async function syncMeetsFromStateBlob(_userId: string, meets: any[]) {
  if (!meets?.length) return;
  const sb = supabaseBrowser();
  for (const m of meets) {
    const row = {
      id: m.id,
      proposer_id: m.proposerId, recipient_id: m.recipientId,
      proposer_name: m.proposerName, recipient_name: m.recipientName,
      time_str: m.time, place: m.place, message: m.message || null,
      status: m.status || 'pending',
    };
    await sb.from('meets').upsert(row, { onConflict: 'id' });
  }
}

// ─── Install on window so the existing Dara code finds it ────────────
export function installWindowStorage() {
  if (typeof window === 'undefined') return;
  (window as any).storage = { get, set, delete: del, list };
}
