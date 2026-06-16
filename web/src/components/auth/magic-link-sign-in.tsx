'use client';

import { useState } from 'react';
import { supabaseBrowser } from '@/lib/supabase/client';

// ─── Magic-link sign-in / sign-up ────────────────────────────────────
// Email-only auth. Supabase emails a link that signs the user in. On first
// sign-in, the user goes through Dara's profile builder before the app.
// Styled with the shared Dara design language (see globals.css).
export default function MagicLinkSignIn() {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');

  const send = async () => {
    setError(''); setBusy(true);
    try {
      const sb = supabaseBrowser();
      const { error } = await sb.auth.signInWithOtp({
        email: email.trim().toLowerCase(),
        options: { emailRedirectTo: window.location.origin },
      });
      if (error) throw error;
      setSent(true);
    } catch (e: any) {
      setError(e.message || 'Could not send link');
    } finally { setBusy(false); }
  };

  return (
    <div style={{ minHeight:'100vh', display:'flex', alignItems:'center', justifyContent:'center', padding:'2rem' }}>
      <div style={{ maxWidth:'440px', width:'100%' }}>
        <div className="dara-wordmark" style={{ marginBottom:'1.5rem' }}>─── D A R A ───</div>
        {!sent ? (<>
          <h1 className="dara-title">Sign <em>in</em>.</h1>
          <div className="dara-rule" />
          <p className="dara-muted" style={{ fontSize:'.95rem', marginBottom:'2rem' }}>
            We'll email you a link. No password — tap the link in your inbox and you're in.
            New here? Same flow; you'll build your profile next.
          </p>
          <input
            type="email" value={email} onChange={e => setEmail(e.target.value)}
            placeholder="you@example.com" autoComplete="email"
            className="dara-input" style={{ marginBottom:'1.25rem' }}
          />
          {error && <div className="dara-error" style={{ marginBottom:'1rem' }}>{error}</div>}
          <button
            onClick={send} disabled={busy || !email.trim()}
            className="dara-btn dara-btn-primary"
          >
            {busy ? 'Sending…' : 'Email me a link →'}
          </button>
        </>) : (
          <div>
            <h1 className="dara-title">Check your <em>inbox</em>.</h1>
            <div className="dara-rule" />
            <p className="dara-muted" style={{ fontSize:'.95rem' }}>
              We sent a link to <strong>{email}</strong>. Open it on this device to finish signing in.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
