import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL || "https://uufabvwilnxktnpygtkq.supabase.co";
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY || "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InV1ZmFidndpbG54a3RucHlndGtxIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzMxMjMwODQsImV4cCI6MjA4ODY5OTA4NH0.5o7nbKNOGb6G9aysA7qeexBGAmy7787kj1FwiGY50gA";

export const supabase = createClient(supabaseUrl, supabaseAnonKey);

const API_URL = "http://localhost:8000";

export async function getAuthToken() {
  const { data } = await supabase.auth.getSession();
  return data?.session?.access_token || null;
}

export async function authFetch(url, options = {}) {
  const token = await getAuthToken();
  if (!token) throw new Error("Not authenticated");
  
  // Prepend API_URL if url doesn't start with http
  const fullUrl = url.startsWith("http") ? url : `${API_URL}${url}`;
  
  const headers = { ...options.headers, Authorization: `Bearer ${token}` };
  
  // Do not set Content-Type to application/json if sending FormData
  if (!(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  
  return fetch(fullUrl, {
    ...options,
    headers,
  });
}
