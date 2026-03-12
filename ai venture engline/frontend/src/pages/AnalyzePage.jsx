import { useState } from "react";
import { useAuth } from "../contexts/AuthContext";
import { authFetch } from "../lib/supabase";
import UploadPanel from "../components/UploadPanel";
import AgentStream from "../components/AgentStream";
import MemoView from "../components/MemoView";

export default function AnalyzePage() {
  const [phase, setPhase] = useState("upload"); // upload | analyzing | results
  const [analysisId, setAnalysisId] = useState(null);
  const [memo, setMemo] = useState(null);
  const { refreshProfile } = useAuth();

  const handleUpload = (id) => {
    setAnalysisId(id);
    setPhase("analyzing");
  };

  const handleComplete = async () => {
    try {
      const res = await authFetch(`/memo?analysis_id=${analysisId}`);
      if (res.ok) setMemo(await res.json());
    } catch { /* ignore */ }
    setPhase("results");
    // Refresh profile to update credit count
    refreshProfile();
  };

  const handleDownloadPdf = async () => {
    try {
      const res = await authFetch(`/memo/pdf?analysis_id=${analysisId}`);
      if (!res.ok) { alert("Failed to generate PDF."); return; }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      const disposition = res.headers.get("Content-Disposition");
      const match = disposition?.match(/filename="(.+)"/);
      a.download = match ? match[1] : "investment-memo.pdf";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch { alert("PDF download failed."); }
  };

  const reset = () => { setPhase("upload"); setAnalysisId(null); setMemo(null); };

  return (
    <main className="px-6 py-4">
      {phase !== "upload" && (
        <div className="max-w-4xl mx-auto mb-4">
          <button onClick={reset} className="text-sm text-slate-600 hover:text-slate-900 transition-colors cursor-pointer">
            ← New Analysis
          </button>
        </div>
      )}
      {phase === "upload" && <UploadPanel onUploadComplete={handleUpload} />}
      {phase === "analyzing" && <AgentStream analysisId={analysisId} onComplete={handleComplete} />}
      {phase === "results" && <MemoView memo={memo} onDownloadPdf={handleDownloadPdf} />}
    </main>
  );
}
