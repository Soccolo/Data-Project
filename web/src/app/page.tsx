'use client';

import { useEffect, useState } from 'react';
import { supabaseBrowser } from '@/lib/supabase/client';
import { installWindowStorage } from '@/lib/storage/adapter';
import MagicLinkSignIn from '@/components/auth/magic-link-sign-in';
import DaraApp from '@/components/dara';

// Top-level entry. Two responsibilities:
//   1. Install the window.storage shim BEFORE the Dara component mounts.
//   2. Wait until we know whether the user is signed in. If not, render
//      a minimal "sign in or up" screen using Supabase magic-link auth.
//      If yes, mount the existing Dara component which takes over.

export default function Page() {
  const [authState, setAuthState] = useState<'loading' | 'signed-out' | 'signed-in'>('loading');
  const [storageReady, setStorageReady] = useState(false);

  useEffect(() => {
    installWindowStorage();
    setStorageReady(true);
    const sb = supabaseBrowser();
    sb.auth.getSession().then(({ data: { session } }) => {
      setAuthState(session ? 'signed-in' : 'signed-out');
    });
    const { data: { subscription } } = sb.auth.onAuthStateChange((_e, session) => {
      setAuthState(session ? 'signed-in' : 'signed-out');
    });
    return () => subscription.unsubscribe();
  }, []);

  if (authState === 'loading' || !storageReady) {
    return <div className="dara-loading">Loading…</div>;
  }
  if (authState === 'signed-out') {
    return <MagicLinkSignIn />;
  }
  return <DaraApp />;
}
