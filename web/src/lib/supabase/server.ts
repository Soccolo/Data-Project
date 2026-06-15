import { createServerClient } from '@supabase/ssr';
import { cookies } from 'next/headers';

// Server-side client for use in API routes and Server Components.
// Reads the auth session from cookies.
export function supabaseServer() {
  const cookieStore = cookies();
  return createServerClient(
    process.env.NEXT_PUBLIC_SUPABASE_URL!,
    process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY!,
    {
      cookies: {
        getAll() { return cookieStore.getAll(); },
        setAll(toSet) {
          try { toSet.forEach(({ name, value, options }) => cookieStore.set(name, value, options)); }
          catch { /* called from a Server Component — ignore */ }
        },
      },
    }
  );
}
