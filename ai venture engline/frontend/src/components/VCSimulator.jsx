import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { XCircle, Eye, ChevronDown, ChevronUp } from 'lucide-react';

const SEVERITY_STYLES = {
  critical: { bg: 'bg-rose-50', border: 'border-rose-200', icon: 'text-rose-500', label: 'DEAL BREAKER' },
  high: { bg: 'bg-amber-50', border: 'border-amber-200', icon: 'text-amber-500', label: 'RED FLAG' },
};

export default function VCSimulator({ slideFeedback, verdict, score }) {
  const [revealed, setRevealed] = useState(0);
  const [expanded, setExpanded] = useState(false);
  const [simStarted, setSimStarted] = useState(false);

  // Filter to only critical/high severity slides with problems
  const rejectionSignals = (slideFeedback || [])
    .filter(sf => (sf.severity === 'critical' || sf.severity === 'high') && sf.problem)
    .slice(0, 5);

  useEffect(() => {
    if (!simStarted || rejectionSignals.length === 0) return;
    if (revealed >= rejectionSignals.length) return;

    const timer = setTimeout(() => {
      setRevealed(prev => prev + 1);
    }, 1200);

    return () => clearTimeout(timer);
  }, [revealed, simStarted, rejectionSignals.length]);

  if (rejectionSignals.length === 0) return null;

  const getOutcome = () => {
    if (score >= 7) return { text: 'Lean Pass → Request Follow-up', color: 'text-emerald-600' };
    if (score >= 5) return { text: 'Likely Pass → Needs Major Fixes', color: 'text-amber-600' };
    return { text: 'Likely Reject → Deck Not Ready', color: 'text-rose-600' };
  };

  const outcome = getOutcome();

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden shadow-sm">
      {/* Header */}
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-6 py-5 flex items-center justify-between hover:bg-slate-50 transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-rose-50 border border-rose-200 flex items-center justify-center">
            <Eye className="w-5 h-5 text-rose-500" />
          </div>
          <div className="text-left">
            <h3 className="text-base font-bold text-slate-900">VC First Impression Simulator</h3>
            <p className="text-xs text-slate-500">See how investors react to your deck in 30 seconds</p>
          </div>
        </div>
        {expanded ? <ChevronUp className="w-5 h-5 text-slate-400" /> : <ChevronDown className="w-5 h-5 text-slate-400" />}
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="overflow-hidden"
          >
            <div className="px-6 pb-6 border-t border-slate-100 pt-4">
              {!simStarted ? (
                <div className="text-center py-6">
                  <p className="text-slate-600 text-sm mb-4">
                    Watch how a VC partner reacts to your deck slide-by-slide.
                  </p>
                  <button
                    onClick={() => { setSimStarted(true); setRevealed(1); }}
                    className="px-6 py-3 bg-slate-900 text-white rounded-xl font-semibold text-sm hover:bg-slate-800 transition-colors cursor-pointer"
                  >
                    ▶ Start Simulation
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="text-xs text-slate-400 font-medium uppercase tracking-wider mb-3">
                    Investor opens your deck...
                  </div>

                  {rejectionSignals.slice(0, revealed).map((signal, i) => {
                    const style = SEVERITY_STYLES[signal.severity] || SEVERITY_STYLES.high;
                    return (
                      <motion.div
                        key={i}
                        initial={{ opacity: 0, x: -20 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ duration: 0.4 }}
                        className={`${style.bg} ${style.border} border rounded-xl p-4`}
                      >
                        <div className="flex items-start gap-3">
                          <XCircle className={`w-5 h-5 ${style.icon} flex-shrink-0 mt-0.5`} />
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 mb-1">
                              <span className="text-xs font-bold text-slate-500">Slide {signal.slide_number || signal.slide}</span>
                              <span className="text-xs font-semibold text-slate-400">—</span>
                              <span className="text-xs font-semibold text-slate-700 capitalize">
                                {(signal.slide_type || signal.type || '').replace(/_/g, ' ')} Problem
                              </span>
                              <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded ${
                                signal.severity === 'critical' ? 'bg-rose-100 text-rose-600' : 'bg-amber-100 text-amber-600'
                              }`}>
                                {style.label}
                              </span>
                            </div>
                            <p className="text-sm text-slate-700 font-medium">{signal.problem}</p>
                            <p className="text-xs text-slate-500 mt-1 italic">
                              Investor thought: "{signal.investor_reaction || signal.reaction}"
                            </p>
                          </div>
                        </div>
                      </motion.div>
                    );
                  })}

                  {/* Final VC Reaction */}
                  {revealed >= rejectionSignals.length && (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.5, duration: 0.5 }}
                      className="mt-4 pt-4 border-t border-slate-200"
                    >
                      <div className="bg-slate-50 border border-slate-200 rounded-xl p-5 text-center">
                        <div className="text-xs text-slate-400 uppercase tracking-wider font-semibold mb-2">
                          Final VC Reaction
                        </div>
                        <div className={`text-lg font-bold ${outcome.color}`}>
                          {outcome.text}
                        </div>
                        <div className="text-xs text-slate-500 mt-2">
                          {rejectionSignals.length} rejection signal{rejectionSignals.length !== 1 ? 's' : ''} detected in first pass
                        </div>
                      </div>
                    </motion.div>
                  )}
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
