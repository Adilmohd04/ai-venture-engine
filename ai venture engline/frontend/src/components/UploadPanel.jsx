import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { authFetch } from "../lib/supabase";
import { UploadCloud, FileText, AlertCircle, CheckCircle2 } from "lucide-react";

export default function UploadPanel({ onUploadComplete }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const inputRef = useRef(null);

  const validate = (file) => {
    if (!file.name.toLowerCase().endsWith(".pdf")) return "Only PDF files are accepted.";
    if (file.size > 20 * 1024 * 1024) return "File exceeds 20 MB limit.";
    return null;
  };

  const upload = async (file) => {
    const err = validate(file);
    if (err) { setError(err); return; }
    setError(null);
    setUploading(true);
    try {
      const form = new FormData();
      form.append("file", file);
      const res = await authFetch("/upload", { method: "POST", body: form });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || `Upload failed (${res.status})`);
      }
      const { analysis_id } = await res.json();
      onUploadComplete(analysis_id);
    } catch (e) {
      setError(e.message);
    } finally {
      setUploading(false);
    }
  };

  const onDrop = (e) => { e.preventDefault(); setDragging(false); if (e.dataTransfer.files[0]) upload(e.dataTransfer.files[0]); };
  const onDragOver = (e) => { e.preventDefault(); setDragging(true); };
  const onDragLeave = () => setDragging(false);

  return (
    <div className="flex flex-col items-center justify-center min-h-[70vh] px-4">
      
      {/* Background Blurs */}
      <div className="fixed inset-0 pointer-events-none z-0 flex items-center justify-center max-w-7xl mx-auto opacity-60">
        <div className="w-[600px] h-[600px] bg-slate-200/50 rounded-full blur-[120px]" />
      </div>

      <div className="relative z-10 text-center mb-12 max-w-2xl mx-auto mt-8">
        <motion.div initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ duration: 0.5 }}>
           <h1 className="text-4xl md:text-5xl font-bold text-slate-900 mb-4 tracking-tight">AI Venture Intelligence</h1>
           <p className="text-slate-600 text-lg">Upload a startup pitch deck to unleash the multi-agent <br className="hidden md:block"/> investment committee for deep analysis.</p>
        </motion.div>
      </div>

      <motion.div
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        onDrop={onDrop} onDragOver={onDragOver} onDragLeave={onDragLeave}
        onClick={() => !uploading && inputRef.current?.click()}
        className={`relative w-full max-w-2xl group cursor-pointer ${uploading ? 'pointer-events-none' : ''}`}
      >
        {/* Animated Border Gradient */}
        <div className={`absolute -inset-0.5 rounded-3xl blur transition-all duration-500 ${
          dragging ? "bg-gradient-to-r from-indigo-400 to-purple-400 opacity-60" : "bg-gradient-to-r from-slate-200 to-slate-100 opacity-40 group-hover:bg-indigo-500/20"
        }`} />

        <div className={`relative flex flex-col items-center justify-center p-16 rounded-[22px] backdrop-blur-xl border-2 border-dashed transition-all duration-300 ${
          dragging ? "bg-indigo-50/80 border-indigo-400/50" : "bg-white shadow-sm border-slate-200 hover:border-indigo-400/40 shadow-sm"
        }`}>
          <input ref={inputRef} type="file" accept=".pdf" className="hidden" onChange={(e) => e.target.files[0] && upload(e.target.files[0])} />
          
          <AnimatePresence mode="wait">
            {uploading ? (
              <motion.div 
                key="uploading"
                initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                className="flex flex-col items-center text-center"
              >
                <div className="relative mb-6">
                  <div className="w-20 h-20 border-4 border-slate-200 border-t-indigo-500 rounded-full animate-spin" />
                  <div className="absolute inset-0 flex items-center justify-center">
                    <FileText className="w-6 h-6 text-indigo-400 animate-pulse" />
                  </div>
                </div>
                <h3 className="text-xl font-bold text-slate-900 mb-2">Extracting Intelligence...</h3>
                <p className="text-slate-600 text-sm">Parsing PDF structure, text, and layout.</p>
              </motion.div>
            ) : (
              <motion.div 
                key="idle"
                initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0 }}
                className="flex flex-col items-center text-center"
              >
                <div className={`w-24 h-24 rounded-full flex items-center justify-center mb-6 transition-transform duration-300 ${
                  dragging ? "bg-indigo-500/20 scale-110" : "bg-slate-50 group-hover:scale-105"
                }`}>
                  <UploadCloud className={`w-12 h-12 ${dragging ? "text-indigo-400" : "text-slate-600 group-hover:text-indigo-400"} transition-colors`} />
                </div>
                <h3 className="text-2xl font-bold text-slate-900 mb-3">Drop your pitch deck here</h3>
                <p className="text-slate-500 text-base mb-6">or click to browse your files</p>
                <div className="flex items-center gap-6 text-sm text-slate-400 font-medium">
                  <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> PDF formats</span>
                  <span className="flex items-center gap-1.5"><CheckCircle2 className="w-4 h-4 text-emerald-500" /> Max 20 MB</span>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </motion.div>

      {error && (
        <motion.div 
          initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}
          className="mt-6 flex items-center gap-2 px-4 py-3 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-sm max-w-md w-full"
        >
          <AlertCircle className="w-5 h-5 shrink-0" />
          <p>{error}</p>
        </motion.div>
      )}

      {/* Trust Badges */}
      {!uploading && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="mt-16 flex flex-wrap justify-center gap-8 text-slate-400 font-medium text-sm">
           <div className="flex items-center gap-2"><svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="11" width="18" height="11" rx="2" ry="2"/><path d="M7 11V7a5 5 0 0110 0v4"/></svg> Secure & Private</div>
           <div className="flex items-center gap-2"><svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg> Instant Analysis</div>
           <div className="flex items-center gap-2"><svg className="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16h16v-8"/><polyline points="14 2 14 8 20 8"/><line x1="12" x2="12" y1="18" y2="12"/><line x1="9" x2="15" y1="15" y2="15"/></svg> PDF Export</div>
        </motion.div>
      )}
    </div>
  );
}
