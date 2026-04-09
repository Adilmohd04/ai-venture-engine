import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

if (!supabaseUrl || !supabaseAnonKey) {
  console.error(
    "Missing Supabase environment variables. Set VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY in your .env file."
  );
}

export const supabase = createClient(supabaseUrl || "", supabaseAnonKey || "", {
  auth: {
    flowType: "pkce",
    persistSession: true,
    autoRefreshToken: true,
  },
});

const API_URL = import.meta.env.VITE_API_URL || "https://ai-venture-engine.onrender.com";

export async function getAuthToken() {
  try {
    const { data } = await supabase.auth.getSession();
    return data?.session?.access_token || null;
  } catch (err) {
    console.error("Failed to get auth token:", err);
    return null;
  }
}

export async function authFetch(url, options = {}) {
  const token = await getAuthToken();
  if (!token) throw new Error("Not authenticated");

  const fullUrl = url.startsWith("http") ? url : `${API_URL}${url}`;

  const headers = { ...options.headers, Authorization: `Bearer ${token}` };

  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  return fetch(fullUrl, {
    ...options,
    headers,
  });
}
