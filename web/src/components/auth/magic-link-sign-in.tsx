'use client';

import { useState } from 'react';
import { supabaseBrowser } from '@/lib/supabase/client';

// ─── Magic-link sign-in / sign-up ────────────────────────────────────
// Email-only auth. Supabase emails a link that signs the user in. On
// first sign-in, they'll go through Dara's existing onboarding (basics
// + kind picker + interview). The legacy username/passphrase flow is
// gone — usernames are picked during the kind step instead.
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
        <div style={{ fontFamily:'Fraunces, serif', fontSize:'0.85rem', letterSpacing:'0.3em', textTransform:'uppercase', color:'#c84e2c', marginBottom:'1.5rem', fontWeight:500 }}>─── D A R A ───</div>
        {!sent ? (<>
          <h1 style={{ fontFamily:'Fraunces, serif', fontSize:'clamp(2rem, 5vw, 3rem)', lineHeight:1.1, fontWeight:400, letterSpacing:'-0.02em', marginBottom:'0.75rem' }}>
            Sign <em style={{ color:'#c84e2c' }}>in</em>.
          </h1>
          <p style={{ fontSize:'0.95rem', lineHeight:1.6, color:'#7a6f64', marginBottom:'2rem' }}>
            We'll email you a link. No password — tap the link in your inbox and you're in. New here? Same flow; you'll set up your profile after.
          </p>
          <input type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="you@example.com" autoComplete="email"
            style={{ width:'100%', marginBottom:'1.25rem', padding:'0.7rem 0', background:'transparent', border:'none', borderBottom:'1px solid #d9cfc1', fontSize:'1rem', color:'#1a1817', outline:'none', boxSizing:'border-box' }} />
          {error && <div style={{ marginBottom:'1rem', padding:'0.7rem 0.9rem', background:'#f4ede1', borderLeft:'3px solid #c84e2c', fontSize:'0.85rem', color:'#9b3a1f' }}>{error}</div>}
          <button onClick={send} disabled={busy || !email.trim()}
            style={{ width:'100%', padding:'0.85rem 1.5rem', background:'#1a1817', color:'#faf6f0', border:'none', fontFamily:'Manrope, sans-serif', fontSize:'0.78rem', letterSpacing:'0.18em', textTransform:'uppercase', fontWeight:600, cursor: busy ? 'wait' : 'pointer', opacity: busy || !email.trim() ? 0.5 : 1 }}>
            {busy ? 'Sending…' : 'Email me a link →'}
          </button>
        </>) : (
          <div>
            <h1 style={{ fontFamily:'Fraunces, serif', fontSize:'2rem', lineHeight:1.2, fontWeight:400, marginBottom:'1rem' }}>Check your inbox.</h1>
            <p style={{ fontSize:'0.95rem', lineHeight:1.6, color:'#7a6f64' }}>We sent a link to <strong>{email}</strong>. Open it on this device to finish signing in.</p>
          </div>
        )}
      </div>
    </div>
  );
}
