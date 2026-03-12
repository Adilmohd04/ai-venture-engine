import { BrowserRouter, Routes, Route, Navigate, useNavigate } from "react-router-dom";
import { useState, useRef, useEffect } from "react";
import { AuthProvider, useAuth } from "./contexts/AuthContext";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import AnalysisPage from "./pages/AnalysisPage";
import AnalyzePage from "./pages/AnalyzePage";
import PublicReportPage from "./pages/PublicReportPage";
import PricingPage from "./pages/PricingPage";

import LandingPage from "./pages/LandingPage";

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen bg-slate-50 flex items-center justify-center text-slate-500">Loading...</div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function AuthRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="min-h-screen bg-slate-50 flex items-center justify-center text-slate-500">Loading...</div>;
  if (user) return <Navigate to="/" replace />;
  return children;
}

function NavBar() {
  const { user, profile, signOut } = useAuth();
  const navigate = useNavigate();
  const [profileOpen, setProfileOpen] = useState(false);
  const dropdownRef = useRef(null);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setProfileOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <nav className="border-b border-slate-200/60 bg-white/80 backdrop-blur-md px-6 py-4 flex items-center justify-between sticky top-0 z-50">
      <div className="flex items-center gap-8">
        <div className="flex items-center gap-2 cursor-pointer group" onClick={() => navigate("/")}>
          <div className="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white shadow-sm group-hover:scale-105 transition-transform duration-300">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
          </div>
          <span className="font-bold text-slate-900 tracking-tight text-lg">Venture Intelligence</span>
        </div>
        {user && (
          <div className="hidden md:flex items-center gap-6">
            <button
              onClick={() => navigate("/dashboard")}
              className="text-sm font-medium text-slate-500 hover:text-indigo-600 transition-colors cursor-pointer"
            >
              Dashboard
            </button>
            <button
              onClick={() => navigate("/pricing")}
              className="text-sm font-medium text-slate-500 hover:text-indigo-600 transition-colors cursor-pointer"
            >
              Pricing
            </button>
          </div>
        )}
      </div>

      <div className="flex items-center gap-5">
        {!user ? (
          <div className="flex items-center gap-3">
             <button
              onClick={() => navigate("/login")}
              className="text-sm font-medium text-slate-600 hover:text-slate-900 transition-colors px-3 py-2 cursor-pointer"
            >
              Log In
            </button>
             <button
              onClick={() => navigate("/login")}
              className="text-sm font-semibold text-white bg-slate-900 hover:bg-slate-800 transition-all px-4 py-2.5 rounded-xl shadow-sm cursor-pointer"
            >
              Sign Up
            </button>
          </div>
        ) : (
          <>
            {profile && (
              <div className="hidden sm:flex items-center gap-2 bg-slate-50 px-3 py-1.5 rounded-full border border-slate-200/60">
                <span className="text-xs font-semibold text-slate-600">
                  {profile.used}/{profile.limit} <span className="font-medium text-slate-400">Credits</span>
                </span>
                {profile.plan === "free" && (
                  <>
                    <div className="w-px h-3 bg-slate-300 mx-1" />
                    <button
                      onClick={() => navigate("/pricing")}
                      className="text-xs font-bold text-indigo-600 hover:text-indigo-700 transition-colors flex items-center gap-1 cursor-pointer"
                    >
                      <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m12 3-1.912 5.813a2 2 0 0 1-1.275 1.275L3 12l5.813 1.912a2 2 0 0 1 1.275 1.275L12 21l1.912-5.813a2 2 0 0 1 1.275-1.275L21 12l-5.813-1.912a2 2 0 0 1-1.275-1.275L12 3Z"/></svg>
                      Upgrade
                    </button>
                  </>
                )}
              </div>
            )}
            <div className="h-6 w-px bg-slate-200 hidden sm:block" />
            
            <div className="relative" ref={dropdownRef}>
              <button 
                onClick={() => setProfileOpen(!profileOpen)}
                className="flex items-center gap-2 focus:outline-none hover:opacity-80 transition-opacity cursor-pointer"
              >
                <div className="w-9 h-9 rounded-full bg-gradient-to-tr from-indigo-100 to-purple-100 border border-indigo-200 flex items-center justify-center text-indigo-700 font-bold shadow-sm">
                  {user.email.charAt(0).toUpperCase()}
                </div>
                <svg className={`w-4 h-4 text-slate-400 transition-transform ${profileOpen ? 'rotate-180' : ''}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m6 9 6 6 6-6"/></svg>
              </button>

              {profileOpen && (
                <div className="absolute right-0 mt-3 w-56 bg-white rounded-2xl shadow-xl border border-slate-200 py-2 z-50 transform origin-top-right transition-all">
                  <div className="px-4 py-3 border-b border-slate-100">
                    <p className="text-sm font-semibold text-slate-900 truncate">{user.email}</p>
                    <p className="text-xs text-slate-500 mt-0.5 capitalize">{profile?.plan || 'Free'} Plan</p>
                  </div>
                  
                  <div className="p-2 border-b border-slate-100 sm:hidden">
                    <div className="px-2 py-2 text-xs font-semibold text-slate-600 flex justify-between">
                      <span>Credits:</span>
                      <span>{profile?.used || 0}/{profile?.limit || 3}</span>
                    </div>
                  </div>

                  <div className="p-2">
                    <button 
                      onClick={() => { setProfileOpen(false); navigate("/dashboard"); }}
                      className="w-full text-left px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-indigo-600 rounded-lg transition-colors flex items-center gap-2 cursor-pointer"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect width="7" height="9" x="3" y="3" rx="1"/><rect width="7" height="5" x="14" y="3" rx="1"/><rect width="7" height="9" x="14" y="12" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/></svg>
                      Dashboard
                    </button>
                    <button 
                      onClick={() => { setProfileOpen(false); navigate("/pricing"); }}
                      className="w-full text-left px-3 py-2 text-sm font-medium text-slate-600 hover:bg-slate-50 hover:text-indigo-600 rounded-lg transition-colors flex items-center gap-2 cursor-pointer"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
                      Billing
                    </button>
                  </div>
                  
                  <div className="p-2 pt-1">
                    <button 
                      onClick={() => { setProfileOpen(false); signOut(); }}
                      className="w-full text-left px-3 py-2 text-sm font-medium text-rose-600 hover:bg-rose-50 rounded-lg transition-colors flex items-center gap-2 cursor-pointer"
                    >
                      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" x2="9" y1="12" y2="12"/></svg>
                      Sign Out
                    </button>
                  </div>
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </nav>
  );
}

function AppRoutes() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 font-sans">
      <NavBar />
      <Routes>
        <Route path="/login" element={<AuthRoute><LoginPage /></AuthRoute>} />
        <Route path="/" element={<LandingPage />} />
        <Route path="/analyze" element={<ProtectedRoute><AnalyzePage /></ProtectedRoute>} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
        <Route path="/analysis/:analysisId" element={<ProtectedRoute><AnalysisPage /></ProtectedRoute>} />
        <Route path="/pricing" element={<ProtectedRoute><PricingPage /></ProtectedRoute>} />
        <Route path="/report/:analysisId" element={<PublicReportPage />} />
      </Routes>
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}
