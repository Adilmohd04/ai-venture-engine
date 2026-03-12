import { useState } from "react";
import { supabase } from "../lib/supabase";

export default function LoginPage() {
  const [mode, setMode] = useState("login"); // login | signup
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      if (mode === "signup") {
        const { error } = await supabase.auth.signUp({
          email,
          password,
          options: { data: { full_name: fullName } },
        });
        if (error) throw error;
        setMessage("Check your email for a confirmation link.");
      } else {
        const { error } = await supabase.auth.signInWithPassword({ email, password });
        if (error) throw error;
      }
    } catch (err) {
      setError(err.message);
    }
    setLoading(false);
  };

  const handleGoogleLogin = async () => {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: "google",
      options: { redirectTo: window.location.origin },
    });
    if (error) setError(error.message);
  };

  return (
    <div className="min-h-screen bg-slate-50 flex font-sans">
      
      {/* Left Side - Branding */}
      <div className="hidden lg:flex flex-1 relative overflow-hidden bg-slate-50 items-center justify-center border-r border-slate-200">
        <div className="absolute inset-0 bg-gradient-to-br from-indigo-900/40 via-purple-900/20 to-zinc-950 z-0"/>
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-500/20 blur-[120px]" />
        
        <div className="relative z-10 max-w-lg px-12 pt-12 pb-24 text-center">
          <div className="mb-8 inline-flex items-center justify-center p-4 bg-white shadow-sm rounded-2xl border border-slate-200 backdrop-blur-xl shadow-2xl">
             <span className="text-6xl">🏦</span>
          </div>
          <h1 className="text-4xl font-bold text-slate-900 mb-6 leading-tight">
            Analyze pitch decks <br/>
            like a top-tier VC.
          </h1>
          <p className="text-xl text-slate-600 mb-12">
            Multi-agent AI debates, deep-dive risk analysis, and comprehensive investor memos.
          </p>

          <div className="grid grid-cols-2 gap-4 text-left">
             <div className="p-4 rounded-xl bg-white shadow-sm border border-slate-200 backdrop-blur-sm">
               <h3 className="text-indigo-400 font-semibold mb-1">Deep Research</h3>
               <p className="text-sm text-slate-9000">Live web validation of claims & metrics</p>
             </div>
             <div className="p-4 rounded-xl bg-white shadow-sm border border-slate-200 backdrop-blur-sm">
               <h3 className="text-purple-400 font-semibold mb-1">Adversarial AI</h3>
               <p className="text-sm text-slate-9000">Bull vs Bear agents debate thesis</p>
             </div>
          </div>
        </div>
      </div>

      {/* Right Side - Auth Form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12 lg:px-24">
        <div className="w-full max-w-md">
          <div className="mb-10 lg:hidden text-center">
             <span className="text-4xl mb-4 inline-block">🏦</span>
             <h1 className="text-2xl font-bold text-slate-900">Venture Intelligence</h1>
          </div>
          
          <div className="text-center mb-10">
            <h2 className="text-3xl font-bold text-slate-900 mb-2">Welcome back</h2>
            <p className="text-slate-600">Sign in to your account to continue</p>
          </div>

          <div className="bg-white shadow-sm border border-slate-200 rounded-2xl p-8 backdrop-blur-md shadow-xl">
            {/* Tabs */}
            <div className="flex mb-8 bg-slate-50/50 rounded-xl p-1 border border-slate-200">
              <button
                onClick={() => setMode("login")}
                className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all cursor-pointer ${
                  mode === "login" 
                    ? "bg-slate-100 text-slate-900 shadow-sm border border-slate-300" 
                    : "text-slate-9000 hover:text-slate-900 border border-transparent"
                }`}
              >
                Log In
              </button>
              <button
                onClick={() => setMode("signup")}
                className={`flex-1 py-2.5 text-sm font-medium rounded-lg transition-all cursor-pointer ${
                  mode === "signup" 
                    ? "bg-slate-100 text-slate-900 shadow-sm border border-slate-300" 
                    : "text-slate-9000 hover:text-slate-900 border border-transparent"
                }`}
              >
                Sign Up
              </button>
            </div>

            {/* Google OAuth */}
            <button
              onClick={handleGoogleLogin}
              className="w-full py-3 bg-white hover:bg-indigo-50 text-zinc-950 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-all mb-6 cursor-pointer shadow-[0_0_20px_-5px_rgba(255,255,255,0.2)]"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24"><path fill="currentColor" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/><path fill="currentColor" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/><path fill="currentColor" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/><path fill="currentColor" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/></svg>
              Continue with Google
            </button>

            <div className="flex items-center gap-4 mb-6">
              <div className="flex-1 h-px bg-slate-100" />
              <span className="text-xs text-slate-9000 uppercase tracking-widest font-medium">or email</span>
              <div className="flex-1 h-px bg-slate-100" />
            </div>

            {/* Email form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              {mode === "signup" && (
                <div>
                  <label className="block text-xs font-medium text-slate-600 mb-1.5">Full Name</label>
                  <input
                    type="text"
                    placeholder="Jane Doe"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    className="w-full px-4 py-3 bg-slate-50/50 border border-slate-200 rounded-xl text-slate-900 text-sm placeholder-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                  />
                </div>
              )}
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Email Address</label>
                <input
                  type="email"
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="w-full px-4 py-3 bg-slate-50/50 border border-slate-200 rounded-xl text-slate-900 text-sm placeholder-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-slate-600 mb-1.5">Password</label>
                <input
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full px-4 py-3 bg-slate-50/50 border border-slate-200 rounded-xl text-slate-900 text-sm placeholder-zinc-600 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-all"
                />
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full py-3 mt-2 bg-indigo-600 hover:bg-indigo-500 border border-indigo-500 disabled:opacity-50 text-white rounded-xl text-sm font-semibold transition-all shadow-[0_0_20px_-5px_rgba(79,70,229,0.4)] cursor-pointer"
              >
                {loading ? "Processing..." : mode === "login" ? "Sign In" : "Create Account"}
              </button>
            </form>

            {error && <p className="text-red-400 text-sm mt-4 text-center bg-red-400/10 p-2 rounded-lg border border-red-500/20">{error}</p>}
            {message && <p className="text-emerald-400 text-sm mt-4 text-center bg-emerald-400/10 p-2 rounded-lg border border-emerald-500/20">{message}</p>}
          </div>

          <p className="text-center text-slate-9000 text-xs mt-8">
            By continuing, you agree to our Terms of Service and Privacy Policy.
          </p>
        </div>
      </div>
    </div>
  );
}
