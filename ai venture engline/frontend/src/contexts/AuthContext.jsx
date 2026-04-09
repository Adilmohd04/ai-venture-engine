import { createContext, useContext, useEffect, useState, useRef } from "react";
import { supabase } from "../lib/supabase";

const AuthContext = createContext({});
const API_URL = import.meta.env.VITE_API_URL || "https://ai-venture-engine.onrender.com";

const AUTH_TIMEOUT_MS = 12000; // 12 seconds max wait for auth to resolve

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);
  const resolvedRef = useRef(false);

  function resolveAuth(sessionUser) {
    if (resolvedRef.current) return;
    resolvedRef.current = true;
    setUser(sessionUser ?? null);
    if (!sessionUser) setLoading(false);
  }

  function handleAuthError(err, context) {
    console.error(`Auth error (${context}):`, err);
    setAuthError(err?.message || "Authentication failed");
    // Clear corrupt session so user can re-login
    supabase.auth.signOut().catch(() => {});
    setUser(null);
    setProfile(null);
    setLoading(false);
    resolvedRef.current = true;
  }

  useEffect(() => {
    resolvedRef.current = false;

    // Safety timeout — never let loading hang forever
    const timeout = setTimeout(() => {
      if (!resolvedRef.current) {
        console.warn("Auth timeout reached — forcing loading to false");
        setAuthError("Authentication timed out");
        setUser(null);
        setLoading(false);
        resolvedRef.current = true;
      }
    }, AUTH_TIMEOUT_MS);

    // Get initial session
    supabase.auth.getSession().then(({ data: { session }, error }) => {
      if (error) {
        handleAuthError(error, "getSession");
        return;
      }
      resolveAuth(session?.user);
      if (session?.user) fetchProfile(session.access_token);
    }).catch((err) => {
      handleAuthError(err, "getSession catch");
    });

    // Listen for auth changes
    const { data: { subscription } } = supabase.auth.onAuthStateChange(
      async (event, session) => {
        try {
          // Handle error-related events
          if (event === "TOKEN_REFRESHED" && !session) {
            handleAuthError(new Error("Token refresh failed"), "onAuthStateChange");
            return;
          }
          if (event === "SIGNED_OUT") {
            setUser(null);
            setProfile(null);
            setAuthError(null);
            setLoading(false);
            resolvedRef.current = true;
            return;
          }

          setUser(session?.user ?? null);
          setAuthError(null);
          if (session?.user) {
            fetchProfile(session.access_token);
          } else {
            setProfile(null);
            setLoading(false);
          }
          resolvedRef.current = true;
        } catch (err) {
          handleAuthError(err, "onAuthStateChange handler");
        }
      }
    );

    return () => {
      clearTimeout(timeout);
      subscription.unsubscribe();
    };
  }, []);

  async function fetchProfile(token) {
    try {
      const res = await fetch(`${API_URL}/api/profile`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setProfile(await res.json());
    } catch { /* ignore profile fetch errors */ }
    setLoading(false);
  }

  async function refreshProfile() {
    const { data } = await supabase.auth.getSession();
    if (data?.session) await fetchProfile(data.session.access_token);
  }

  async function signOut() {
    await supabase.auth.signOut();
    setUser(null);
    setProfile(null);
    setAuthError(null);
  }

  return (
    <AuthContext.Provider value={{ user, profile, loading, authError, signOut, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
