import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { authFetch } from "../lib/supabase";
import MemoView from "../components/MemoView";
import ShareReportModal from "../components/ShareReportModal";
import ImprovementTracker from "../components/ImprovementTracker";
import VCSimulator from "../components/VCSimulator";

export default function AnalysisPage() {
  const { analysisId } = useParams();
  const [memo, setMemo] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showShareModal, setShowShareModal] = useState(false);
  const navigate = useNavigate();

  useEffect(() => {
    loadAnalysis();
  }, [analysisId]);

  async function loadAnalysis() {
    setLoading(true);
    try {
      const res = await authFetch(`/api/analyses/${analysisId}`);
      if (res.ok) {
        const data = await res.json();
        setMemo(data);
        // Load history for this startup
        const name = data.structured_extraction?.startup_name || data.startup_overview?.split(" is ")[0];
        if (name) {
          const hRes = await authFetch(`/api/history/${encodeURIComponent(name)}`);
          if (hRes.ok) setHistory(await hRes.json());
        }
      }
    } catch { /* ignore */ }
    setLoading(false);
  }

  const handleDownloadPdf = async () => {
    try {
      const res = await authFetch(`/memo/pdf?analysis_id=${analysisId}`);
      if (!res.ok) { alert("PDF generation failed."); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "investment-memo.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch { alert("PDF download failed."); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center text-slate-500 font-medium">Loading analysis...</div>;
  if (!memo) return <div className="min-h-screen flex items-center justify-center text-slate-500 font-medium">Analysis not found.</div>;

  return (
    <div className="min-h-screen bg-slate-50 relative pb-20">
      {/* Back button */}
      <div className="max-w-4xl mx-auto pt-4 px-4">
        <button
          onClick={() => navigate("/dashboard")}
          className="text-sm text-slate-600 hover:text-slate-900 transition-colors cursor-pointer"
        >
          ← Back to Deal Flow
        </button>
      </div>

      {/* Score Timeline (if multiple analyses for same startup) */}
      {history.length > 1 && (
        <>
          <div className="max-w-4xl mx-auto px-4 mt-4">
            <ImprovementTracker history={history} currentAnalysisId={analysisId} />
          </div>
          
          <div className="max-w-4xl mx-auto px-4 mt-4">
            <div className="bg-white border border-slate-200 rounded-xl p-5">
              <h3 className="text-sm font-semibold text-slate-900 mb-3">📈 All Analyses</h3>
              <div className="flex items-end gap-2 h-24">
                {history.map((h, i) => {
                  const height = Math.max(10, (h.final_score / 10) * 100);
                  const isCurrent = h.analysis_id === analysisId;
                  return (
                    <div key={i} className="flex flex-col items-center flex-1 gap-1">
                      <span className={`text-xs font-mono font-medium ${isCurrent ? "text-indigo-600" : "text-slate-500"}`}>
                        {h.final_score?.toFixed(1)}
                      </span>
                      <div
                        className={`w-full rounded-t transition-all ${isCurrent ? "bg-indigo-500" : "bg-slate-200 hover:bg-slate-300"} cursor-pointer`}
                        style={{ height: `${height}%` }}
                        onClick={() => navigate(`/analysis/${h.analysis_id}`)}
                        role="button"
                        tabIndex={0}
                      />
                      <span className="text-[10px] text-slate-500 font-medium tracking-wide">
                        {new Date(h.created_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        </>
      )}

      <MemoView memo={memo} onDownloadPdf={handleDownloadPdf} />

      {/* VC First Impression Simulator */}
      {memo.slide_feedback && memo.slide_feedback.length > 0 && (
        <div className="max-w-4xl mx-auto px-4 mt-6">
          <VCSimulator
            slideFeedback={memo.slide_feedback}
            verdict={memo.verdict}
            score={memo.final_score}
          />
        </div>
      )}
      
      {/* Share Report Button */}
      <div className="max-w-4xl mx-auto px-4 mt-8 mb-8">
        <button
          onClick={() => setShowShareModal(true)}
          className="w-full bg-white border border-indigo-200 text-indigo-600 py-3.5 px-6 rounded-xl font-semibold hover:bg-indigo-50 hover:border-indigo-300 transition-all shadow-sm flex items-center justify-center gap-2"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 12v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8"/><polyline points="16 6 12 2 8 6"/><line x1="12" y1="2" x2="12" y2="15"/></svg>
          Share Report Publicly
        </button>
      </div>
      
      {/* Share Modal */}
      {showShareModal && (
        <ShareReportModal
          analysisId={analysisId}
          onClose={() => setShowShareModal(false)}
        />
      )}
    </div>
  );
}
