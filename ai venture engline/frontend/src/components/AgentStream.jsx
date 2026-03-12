import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { getAuthToken } from "../lib/supabase";
import PriorityBadge from "./PriorityBadge";

const AGENT_META = {
  research:       { name: "Research Agent",  avatar: "🔎", color: "text-blue-600", bg: "bg-blue-50", border: "border-blue-100" },
  bull:           { name: "Bull Analyst",    avatar: "📈", color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-100" },
  bear:           { name: "Bear Analyst",    avatar: "📉", color: "text-rose-600", bg: "bg-rose-50", border: "border-rose-100" },
  bull_rebuttal:  { name: "Bull Rebuttal",   avatar: "⚔️", color: "text-emerald-600", bg: "bg-emerald-50", border: "border-emerald-100" },
  bear_rebuttal:  { name: "Bear Rebuttal",   avatar: "🛑", color: "text-orange-600", bg: "bg-orange-50", border: "border-orange-100" },
  risk:           { name: "Risk Engine",     avatar: "⚠️", color: "text-amber-600", bg: "bg-amber-50", border: "border-amber-100" },
  judge:          { name: "Judge",           avatar: "⚖️", color: "text-purple-600", bg: "bg-purple-50", border: "border-purple-100" },
};

// Sanitize markdown emphasis markers from streaming output
const sanitizeMarkdown = (text) => {
  if (!text) return text;
  
  // Remove triple asterisks (bold+italic)
  text = text.replace(/\*\*\*(.*?)\*\*\*/g, '$1');
  
  // Remove double asterisks (bold)
  text = text.replace(/\*\*(.*?)\*\*/g, '$1');
  
  // Remove single asterisks (italic)
  text = text.replace(/\*(.*?)\*/g, '$1');
  
  // Remove underscores for emphasis
  text = text.replace(/__(.*?)__/g, '$1');
  text = text.replace(/_(.*?)_/g, '$1');
  
  return text;
};

// Filter out JSON blocks from risk engine output
const filterJSON = (text) => {
  if (!text) return text;
  
  // Remove JSON objects (including nested structures)
  text = text.replace(/\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}/g, '');
  
  // Remove JSON arrays
  text = text.replace(/\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]/g, '');
  
  // Clean up extra whitespace left behind
  text = text.replace(/\n\s*\n\s*\n/g, '\n\n');
  
  return text.trim();
};



export default function AgentStream({ analysisId, onComplete }) {
  const [agents, setAgents] = useState([]);
  const [error, setError] = useState(null);
  const [currentPhase, setCurrentPhase] = useState("Initializing intelligence engine...");
  const [priority, setPriority] = useState(false);
  const bottomRef = useRef(null);

  useEffect(() => {
    let es;
    (async () => {
      const token = await getAuthToken();
      es = new EventSource(`/stream-analysis?analysis_id=${analysisId}&token=${token}`);

      es.addEventListener("analysis_start", (e) => {
        try {
          const d = JSON.parse(e.data);
          if (d.priority) setPriority(true);
        } catch { /* ignore */ }
      });

      es.addEventListener("agent_start", (e) => {
        const d = JSON.parse(e.data);
        const meta = AGENT_META[d.agent] || { name: d.agent };
        setCurrentPhase(`${meta.name} is running...`);
        setAgents((prev) => {
          if (prev.find(a => a.id === d.agent)) return prev;
          return [...prev, { id: d.agent, content: "", status: "thinking" }];
        });
      });

      es.addEventListener("agent_token", (e) => {
        const d = JSON.parse(e.data);
        setAgents((prev) =>
          prev.map((a) => a.id === d.agent ? { ...a, content: a.content + d.content, status: "streaming" } : a)
        );
      });

      es.addEventListener("agent_complete", (e) => {
        const d = JSON.parse(e.data);
        setAgents((prev) =>
          prev.map((a) => a.id === d.agent ? { ...a, status: "complete" } : a)
        );
      });

      es.addEventListener("pipeline_complete", () => { 
        setCurrentPhase("Analysis complete. Generating memo...");
        es.close(); 
        setTimeout(onComplete, 1500); 
      });

      es.addEventListener("error", (e) => {
        try { const d = JSON.parse(e.data); setError(d.message); } catch { setError("Connection lost. Trying to reconnect..."); }
      });
      es.onerror = () => { /* let browser reconnect */ };

    })();
    return () => { if (es) es.close(); };
  }, [analysisId, onComplete]);

  useEffect(() => { 
    if (bottomRef.current) {
      bottomRef.current.scrollIntoView({ behavior: "smooth", block: "end" });
    }
  }, [agents]);

  return (
    <div className="max-w-4xl mx-auto py-8 px-4">
      {/* Pipeline Status Header */}
      <motion.div 
        initial={{ opacity: 0, y: -20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white shadow-sm border border-slate-200 rounded-2xl p-6 mb-8 backdrop-blur-xl shadow-2xl flex items-center justify-between sticky top-4 z-40"
      >
        <div className="flex items-center gap-4">
          <div className="relative flex items-center justify-center w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
             <div className="absolute inset-0 rounded-xl border border-indigo-500/30 animate-[spin_4s_linear_infinite]" style={{ borderTopColor: 'transparent', borderRightColor: 'transparent' }}/>
             <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>
          </div>
          <div>
            <div className="text-xs font-semibold text-slate-9000 uppercase tracking-widest mb-1">System Status</div>
            <div className="text-lg font-bold text-slate-900 flex items-center gap-2">
              {currentPhase}
              <motion.span 
                animate={{ opacity: [0, 1, 0] }}
                transition={{ duration: 1.5, repeat: Infinity }}
                className="inline-block w-1.5 h-1.5 rounded-full bg-indigo-500"
              />
            </div>
          </div>
        </div>
        {priority && <PriorityBadge />}
      </motion.div>
      
      {/* Agent Timeline */}
      <div className="space-y-6 relative before:absolute before:inset-0 before:ml-8 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-slate-200 before:to-transparent">
        <AnimatePresence>
          {agents.map((a, index) => {
            const meta = AGENT_META[a.id] || { name: a.id, avatar: "🤖", color: "text-slate-600", bg: "bg-slate-100", border: "border-slate-300" };
            const isLatest = index === agents.length - 1;
            
            return (
              <motion.div 
                key={a.id}
                initial={{ opacity: 0, y: 20, scale: 0.95 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active"
              >
                {/* Timeline dot */}
                <div className={`flex items-center justify-center w-10 h-10 rounded-full border border-slate-200 bg-white text-lg shadow-sm shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10 ${a.status !== 'complete' ? 'ring-4 ring-indigo-50 border-indigo-200' : ''}`}>
                  {meta.avatar}
                </div>
                
                {/* Card */}
                <div className={`w-[calc(100%-4rem)] md:w-[calc(50%-3rem)] p-5 rounded-2xl bg-white shadow-sm border ${a.status === 'streaming' ? 'border-indigo-200 shadow-indigo-500/5' : 'border-slate-200'} transition-all duration-300`}>
                  <div className="flex items-center justify-between mb-4 border-b border-slate-100 pb-3">
                    <span className={`font-semibold ${meta.color} flex items-center gap-2`}>
                      {meta.name}
                      {a.status === 'thinking' && <motion.span animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }} className="inline-block w-4 h-4 border-2 border-current border-t-transparent rounded-full opacity-70"/>}
                    </span>
                    <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border ${
                      a.status === 'complete' ? 'bg-emerald-50 text-emerald-600 border-emerald-100' : 
                      a.status === 'streaming' ? 'bg-indigo-50 text-indigo-600 border-indigo-100' : 
                      'bg-amber-50 text-amber-600 border-amber-100'
                    }`}>
                      {a.status}
                    </span>
                  </div>
                  
                  <div className="text-slate-700 text-sm leading-relaxed overflow-hidden relative">
                    <div className={`max-h-64 overflow-y-auto pr-2 custom-scrollbar ${isLatest ? 'animate-fade-in' : ''}`}>
                      {a.content ? (
                        <div className="prose prose-sm max-w-none prose-slate prose-p:my-2 prose-headings:my-3 prose-headings:text-slate-900 prose-strong:text-slate-900 prose-strong:font-semibold">
                          <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {a.id === 'risk' ? filterJSON(sanitizeMarkdown(a.content)) : sanitizeMarkdown(a.content)}
                          </ReactMarkdown>
                        </div>
                      ) : (
                        <span className="text-slate-400 italic flex items-center gap-2">
                          <span className="flex space-x-1">
                            <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.4, repeat: Infinity, delay: 0 }} className="w-1.5 h-1.5 bg-slate-400 rounded-full"/>
                            <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.4, repeat: Infinity, delay: 0.2 }} className="w-1.5 h-1.5 bg-slate-400 rounded-full"/>
                            <motion.span animate={{ opacity: [0.3, 1, 0.3] }} transition={{ duration: 1.4, repeat: Infinity, delay: 0.4 }} className="w-1.5 h-1.5 bg-slate-400 rounded-full"/>
                          </span>
                          Processing analysis...
                        </span>
                      )}
                    </div>
                    {/* Bottom gradient fade for active agents to indicate more content */}
                    {a.status === 'streaming' && (
                      <div className="absolute bottom-0 left-0 right-0 h-10 bg-gradient-to-t from-white to-transparent pointer-events-none"/>
                    )}
                  </div>
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {error && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="mt-8 text-rose-400 bg-rose-900/20 border border-rose-800/50 rounded-xl p-4 text-center text-sm font-medium">
          {error}
        </motion.div>
      )}
      
      {/* Invisible element to auto-scroll to */}
      <div ref={bottomRef} className="h-20" />
    </div>
  );
}
