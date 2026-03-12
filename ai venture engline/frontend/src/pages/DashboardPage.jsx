import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { authFetch } from "../lib/supabase";
import { useAuth } from "../contexts/AuthContext";
import TeamPanel from "../components/TeamPanel";

const VERDICT_COLORS = {
  "Strong Pass": "text-green-700 bg-green-50 border border-green-200",
  "Pass": "text-emerald-700 bg-emerald-50 border border-emerald-200",
  "Lean Pass": "text-yellow-700 bg-yellow-50 border border-yellow-200",
  "Lean Fail": "text-orange-700 bg-orange-50 border border-orange-200",
  "Fail": "text-red-700 bg-red-50 border border-red-200",
  "Strong Fail": "text-red-800 bg-red-100 border border-red-300",
};

export default function DashboardPage() {
  const [analyses, setAnalyses] = useState([]);
  const [loading, setLoading] = useState(true);
  const [paymentStatus, setPaymentStatus] = useState(null);
  const [filter, setFilter] = useState("mine");
  const { profile, refreshProfile } = useAuth();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();

  useEffect(() => {
    loadAnalyses();
    handlePaymentReturn();
  }, []);

  useEffect(() => {
    loadAnalyses();
  }, [filter, profile?.team_id]);

  async function handlePaymentReturn() {
    const paymentId = searchParams.get("paymentId");
    const payerId = searchParams.get("PayerID");
    const cancelled = searchParams.get("payment") === "cancelled";

    if (cancelled) {
      setPaymentStatus({ type: "error", message: "Payment was cancelled" });
      // Clean up URL
      searchParams.delete("payment");
      setSearchParams(searchParams);
      return;
    }

    if (paymentId && payerId) {
      try {
        setPaymentStatus({ type: "processing", message: "Completing payment..." });
        
        const res = await authFetch("/api/paypal/execute-payment", {
          method: "POST",
          body: JSON.stringify({ payment_id: paymentId, payer_id: payerId }),
        });

        if (res.ok) {
          const data = await res.json();
          setPaymentStatus({ 
            type: "success", 
            message: `Payment successful! ${data.credits_added > 0 ? `${data.credits_added} credits added` : 'Upgraded to unlimited plan'}` 
          });
          
          // Refresh profile to show new credits
          if (refreshProfile) await refreshProfile();
          
          // Clean up URL
          searchParams.delete("paymentId");
          searchParams.delete("PayerID");
          setSearchParams(searchParams);
        } else {
          const error = await res.json();
          setPaymentStatus({ type: "error", message: error.detail || "Payment failed" });
        }
      } catch (error) {
        setPaymentStatus({ type: "error", message: "Payment processing failed" });
      }
    }
  }

  async function loadAnalyses() {
    try {
      let url = "/api/analyses";
      if (filter === "team" && profile?.team_id) {
        url = `/api/teams/${profile.team_id}/analyses`;
      }
      const res = await authFetch(url);
      if (res.ok) setAnalyses(await res.json());
    } catch { /* ignore */ }
    setLoading(false);
  }

  const scoreColor = (score) => {
    if (score >= 7) return "text-green-600";
    if (score >= 5) return "text-yellow-600";
    if (score >= 3) return "text-orange-600";
    return "text-red-600";
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 pt-10 pb-20 px-4 sm:px-6">
      <div className="max-w-6xl mx-auto">
        {/* Team Panel */}
        <TeamPanel />

        {/* Payment Status Banner */}
        {paymentStatus && (
          <div className={`mb-8 rounded-2xl p-5 flex items-center gap-4 ${
            paymentStatus.type === "success" ? "bg-emerald-50 border border-emerald-200" :
            paymentStatus.type === "error" ? "bg-rose-50 border border-rose-200" :
            "bg-indigo-50 border border-indigo-200"
          }`}>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 ${
              paymentStatus.type === "success" ? "bg-emerald-100 text-emerald-600" :
              paymentStatus.type === "error" ? "bg-rose-100 text-rose-600" :
              "bg-indigo-100 text-indigo-600"
            }`}>
              {paymentStatus.type === "success" ? "✓" : paymentStatus.type === "error" ? "✕" : "⟳"}
            </div>
            <div className="flex-1">
              <p className={`text-sm font-medium ${
                paymentStatus.type === "success" ? "text-emerald-700" :
                paymentStatus.type === "error" ? "text-rose-700" :
                "text-indigo-700"
              }`}>
                {paymentStatus.message}
              </p>
            </div>
            <button
              onClick={() => setPaymentStatus(null)}
              className="text-slate-400 hover:text-slate-600 transition-colors"
            >
              ✕
            </button>
          </div>
        )}

        {/* Header */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between mb-10 gap-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight text-slate-900 mb-1">Deal Flow</h1>
            <p className="text-slate-600 text-sm flex items-center gap-2">
              <span className="flex items-center justify-center w-5 h-5 rounded-full bg-indigo-500/10 text-indigo-600 font-medium text-xs">{analyses.length}</span>
              {analyses.length === 1 ? "analysis" : "analyses"} history · {" "}
              <span className="text-slate-500">{profile?.used ?? 0}/{profile?.limit ?? 3} credits used</span>
            </p>
          </div>
          <div className="flex items-center gap-3 w-full sm:w-auto">
            <button
              onClick={() => navigate("/analyze")}
              className="flex-1 sm:flex-none px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl text-sm font-medium cursor-pointer transition-all shadow-[0_0_20px_-5px_rgba(79,70,229,0.4)] flex items-center justify-center gap-2"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" x2="12" y1="3" y2="15"/></svg>
              Upload Deck
            </button>
            {profile?.plan === "free" && (
              <button
                onClick={() => navigate("/pricing")}
                className="flex-1 sm:flex-none px-5 py-2.5 bg-white border border-slate-200 hover:bg-slate-100 text-slate-900 rounded-xl text-sm font-medium cursor-pointer transition-colors"
              >
                Upgrade Plan
              </button>
            )}
          </div>
        </div>

        {/* Analysis Filter Toggle */}
        {profile?.team_id && (
          <div className="flex items-center gap-1 mb-8 bg-white border border-slate-200 rounded-xl p-1 w-fit">
            <button
              onClick={() => setFilter("mine")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === "mine"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              My Analyses
            </button>
            <button
              onClick={() => setFilter("team")}
              className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                filter === "team"
                  ? "bg-indigo-600 text-white"
                  : "text-slate-600 hover:text-slate-900 hover:bg-slate-50"
              }`}
            >
              Team Analyses
            </button>
          </div>
        )}

        {/* Low Credits Warning */}
        {profile && profile.used >= profile.limit && (
          <div className="bg-rose-50 border border-rose-200 rounded-2xl p-5 mb-8 flex items-start sm:items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-rose-100 flex items-center justify-center flex-shrink-0 text-rose-600">
               <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" x2="12" y1="8" y2="12"/><line x1="12" x2="12.01" y1="16" y2="16"/></svg>
            </div>
            <div className="flex-1">
              <h3 className="text-rose-700 font-semibold text-sm mb-0.5">Limit Exceeded</h3>
              <p className="text-rose-600 text-sm">
                You've used all {profile.limit} credits on the {profile.plan} plan.
              </p>
            </div>
            <button
              onClick={() => navigate("/pricing")}
              className="px-4 py-2 bg-rose-600 hover:bg-rose-500 text-white rounded-lg text-sm font-medium cursor-pointer transition-colors"
            >
              View Pricing
            </button>
          </div>
        )}

        {profile && profile.used >= profile.limit * 0.8 && profile.used < profile.limit && (
          <div className="bg-amber-50 border border-amber-200 rounded-2xl p-5 mb-8 flex items-center gap-4">
            <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center flex-shrink-0 text-amber-600">
               <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" x2="12" y1="9" y2="13"/><line x1="12" x2="12.01" y1="17" y2="17"/></svg>
            </div>
            <div className="flex-1">
              <h3 className="text-amber-700 font-semibold text-sm mb-0.5">Running Low on Credits</h3>
              <p className="text-amber-600 text-sm">
                You have {profile.limit - profile.used} credits remaining.
              </p>
            </div>
          </div>
        )}

        {/* Table */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-500 gap-4">
             <div className="w-8 h-8 rounded-full border-2 border-indigo-500 border-t-transparent animate-spin"/>
             <p className="text-sm font-medium">Loading analyses...</p>
          </div>
        ) : analyses.length === 0 ? (
          <div className="text-center py-24 bg-white shadow-sm border border-slate-200 rounded-3xl backdrop-blur-sm border-dashed">
            <div className="w-20 h-20 mx-auto rounded-full bg-slate-50 flex items-center justify-center mb-6">
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-indigo-600"><path d="M14 2H6a2 2 0 0 0-2 2v16h16v-8"/><polyline points="14 2 14 8 20 8"/><line x1="12" x2="12" y1="18" y2="12"/><line x1="9" x2="15" y1="15" y2="15"/></svg>
            </div>
            <p className="text-slate-900 font-semibold text-lg mb-2">No analyses yet</p>
            <p className="text-slate-500 text-sm max-w-sm mx-auto mb-8">Upload your first startup pitch deck to get a comprehensive VC-grade investment memo.</p>
            <button
              onClick={() => navigate("/analyze")}
              className="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl font-medium cursor-pointer shadow-lg shadow-indigo-500/20 transition-all"
            >
              Upload Deck Now
            </button>
          </div>
        ) : (
          <div className="bg-white shadow-sm border border-slate-200 rounded-2xl overflow-hidden backdrop-blur-md shadow-2xl">
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="bg-white shadow-sm border-b border-slate-200 text-xs font-semibold text-slate-600 uppercase tracking-widest">
                  <th className="py-4 px-6 font-medium">Startup</th>
                  <th className="py-4 px-6 hidden md:table-cell font-medium">Industry</th>
                  {filter === "team" && <th className="py-4 px-6 hidden md:table-cell font-medium">Creator</th>}
                  <th className="py-4 px-6 text-center font-medium">Score</th>
                  <th className="py-4 px-6 text-center font-medium">Verdict</th>
                  <th className="py-4 px-6 text-right font-medium">Date</th>
                  <th className="py-4 px-6 w-10"></th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {analyses.map((a) => (
                  <tr
                    key={a.id}
                    onClick={() => navigate(`/analysis/${a.analysis_id}`)}
                    className="hover:bg-slate-50 cursor-pointer transition-all group"
                  >
                    <td className="py-4 px-6">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 rounded-lg bg-slate-50 flex items-center justify-center text-slate-600 font-bold border border-slate-200 group-hover:border-indigo-300 group-hover:bg-indigo-50/50 group-hover:text-indigo-600 transition-colors">
                          {a.startup_name ? a.startup_name.charAt(0).toUpperCase() : "?"}
                        </div>
                        <div>
                           <div className="text-slate-900 font-semibold flex items-center gap-2">
                              {a.startup_name || "Unknown"}
                              {a.stage && <span className="px-2 py-0.5 rounded text-[10px] font-medium bg-slate-100 text-slate-600 tracking-wider uppercase">{a.stage}</span>}
                           </div>
                           <div className="text-xs text-slate-500 mt-0.5">Deep Analysis ✓</div>
                        </div>
                      </div>
                    </td>
                    <td className="py-4 px-6 text-slate-600 text-sm hidden md:table-cell">
                      {a.industry || "—"}
                    </td>
                    {filter === "team" && (
                      <td className="py-4 px-6 text-slate-600 text-sm hidden md:table-cell">
                        {a.full_name || a.user_id || "—"}
                      </td>
                    )}
                    <td className="py-4 px-6 text-center">
                      <span className={`inline-flex items-center justify-center w-9 h-9 rounded-lg bg-slate-50 border border-slate-200 font-mono font-bold text-sm ${scoreColor(a.final_score)}`}>
                        {a.final_score?.toFixed(1) ?? "—"}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-center">
                      <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-xs font-semibold ${VERDICT_COLORS[a.verdict] || "text-slate-600 bg-slate-50 border border-slate-200"}`}>
                        <span className="w-1.5 h-1.5 rounded-full bg-current mr-1.5 opacity-60"></span>
                        {a.verdict || "Pending"}
                      </span>
                    </td>
                    <td className="py-4 px-6 text-right text-slate-500 text-sm font-medium">
                      {a.created_at ? new Date(a.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' }) : "—"}
                    </td>
                    <td className="py-4 px-6 text-right text-slate-300 group-hover:text-indigo-500 transition-colors">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="m9 18 6-6-6-6"/></svg>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
