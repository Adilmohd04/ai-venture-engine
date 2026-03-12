import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  ArrowRight, Upload, Search, TrendingUp, TrendingDown, Scale, FileText,
  AlertTriangle, CheckCircle2, XCircle, Sparkles, Shield, Zap, Activity
} from 'lucide-react';

const FADE_UP = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5 } }
};

const STAGGER = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { staggerChildren: 0.1 } }
};

export default function LandingPage() {
  const navigate = useNavigate();
  const { user } = useAuth();

  const handleCTA = () => navigate(user ? '/analyze' : '/login');

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 overflow-x-hidden selection:bg-indigo-500/20">
      <div className="fixed inset-0 z-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-indigo-500/10 blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[50%] h-[50%] rounded-full bg-purple-500/10 blur-[120px]" />
      </div>

      <div className="relative z-10">

        {/* HERO — outcome-focused */}
        <section className="pt-28 pb-20 px-6 max-w-7xl mx-auto flex flex-col items-center text-center">
          <motion.div initial="hidden" animate="visible" variants={STAGGER} className="space-y-8 max-w-4xl">
            <motion.div variants={FADE_UP} className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 text-indigo-600 text-sm font-medium border border-indigo-200">
              <span className="flex h-2 w-2 rounded-full bg-indigo-500 animate-pulse" />
              Free to try — no credit card required
            </motion.div>

            <motion.h1 variants={FADE_UP} className="text-5xl md:text-7xl font-bold tracking-tight text-slate-900 leading-[1.08]">
              See the exact reasons<br/>
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">
                investors would reject your pitch.
              </span>
            </motion.h1>

            <motion.p variants={FADE_UP} className="text-lg md:text-xl text-slate-600 max-w-2xl mx-auto leading-relaxed">
              Upload your pitch deck. In 30 seconds, get a VC-grade investment memo with your score, 
              deal breakers, and exactly what to fix — before you walk into the room.
            </motion.p>

            <motion.div variants={FADE_UP} className="flex flex-col sm:flex-row items-center justify-center gap-4 pt-4">
              <button onClick={handleCTA}
                className="w-full sm:w-auto px-8 py-4 rounded-xl bg-indigo-600 text-white font-semibold text-lg hover:bg-indigo-500 transition-all flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20 hover:scale-105 active:scale-95 cursor-pointer">
                Analyze My Deck Free <ArrowRight className="w-5 h-5" />
              </button>
              <span className="text-sm text-slate-500">3 free analyses included</span>
            </motion.div>
          </motion.div>

          {/* Pipeline Visual */}
          <motion.div initial={{ opacity: 0, y: 40 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.8 }} className="mt-20 w-full max-w-5xl">
            <div className="relative p-6 rounded-2xl bg-white border border-slate-200 shadow-xl overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/5 to-purple-500/5" />
              <div className="relative flex flex-col md:flex-row items-center justify-between gap-4 md:gap-0">
                {[
                  { icon: Upload, label: "Upload PDF", color: "text-slate-600" },
                  { icon: Search, label: "AI Research", color: "text-blue-600" },
                  { icon: TrendingUp, label: "Bull Case", color: "text-emerald-600" },
                  { icon: TrendingDown, label: "Bear Case", color: "text-rose-600" },
                  { icon: Scale, label: "Verdict", color: "text-purple-600" },
                  { icon: FileText, label: "Full Memo", color: "text-amber-600" }
                ].map((step, i, arr) => (
                  <React.Fragment key={i}>
                    <motion.div whileHover={{ y: -5 }} className="flex flex-col items-center gap-3 z-10">
                      <div className={`w-14 h-14 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-center shadow-sm ${step.color}`}>
                        <step.icon className="w-6 h-6" />
                      </div>
                      <span className="text-xs font-medium text-slate-600">{step.label}</span>
                    </motion.div>
                    {i < arr.length - 1 && (
                      <div className="hidden md:block flex-1 h-px bg-slate-200 mx-2 relative overflow-hidden">
                        <motion.div className="absolute inset-0 bg-indigo-400 origin-left"
                          initial={{ scaleX: 0 }} animate={{ scaleX: 1 }}
                          transition={{ duration: 1, delay: 1 + (i * 0.5), repeat: Infinity, repeatType: "loop", repeatDelay: 3 }} />
                      </div>
                    )}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </motion.div>
        </section>

        {/* SOCIAL PROOF — what you actually get */}
        <section className="py-20 px-6 max-w-7xl mx-auto border-t border-slate-200">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">What founders discover</h2>
            <p className="text-slate-600 max-w-xl mx-auto">Real analysis output. Real insights. No fluff.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-5xl mx-auto">
            <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }}
              className="p-8 rounded-2xl bg-white border border-slate-200 shadow-sm">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-2xl font-bold text-slate-900">Sentinel AI</h3>
                  <p className="text-slate-500 text-sm">Cybersecurity • Series A • $15M raise</p>
                </div>
                <div className="text-right">
                  <div className="text-4xl font-bold text-emerald-600">8.2</div>
                  <div className="text-xs text-emerald-600 font-semibold mt-1">STRONG PASS</div>
                </div>
              </div>
              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-2 text-sm text-slate-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" /> 148% NRR — top 1% retention
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" /> CAC/ACV ratio 0.11 — excellent unit economics
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" /> SECRET clearance + DARPA contract = deep moat
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-700">
                  <XCircle className="w-4 h-4 text-rose-500 shrink-0" /> 47-day sales cycle limits velocity
                </div>
              </div>
              <div className="text-xs text-slate-400 border-t border-slate-100 pt-3">AI computed CAC/ACV, NRR signals, and moat indicators automatically</div>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: 0.1 }}
              className="p-8 rounded-2xl bg-white border border-slate-200 shadow-sm">
              <div className="flex justify-between items-start mb-6">
                <div>
                  <h3 className="text-2xl font-bold text-slate-900">CarbonOS</h3>
                  <p className="text-slate-500 text-sm">Climate Tech • Seed • $3M raise</p>
                </div>
                <div className="text-right">
                  <div className="text-4xl font-bold text-amber-600">5.4</div>
                  <div className="text-xs text-amber-600 font-semibold mt-1">LEAN FAIL</div>
                </div>
              </div>
              <div className="space-y-3 mb-6">
                <div className="flex items-center gap-2 text-sm text-slate-700">
                  <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" /> $82B TAM — massive market
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-700">
                  <XCircle className="w-4 h-4 text-rose-500 shrink-0" /> No revenue disclosed — cap traction at 5
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-700">
                  <XCircle className="w-4 h-4 text-rose-500 shrink-0" /> No competitive moat identified
                </div>
                <div className="flex items-center gap-2 text-sm text-slate-700">
                  <XCircle className="w-4 h-4 text-rose-500 shrink-0" /> Team lacks direct climate tech experience
                </div>
              </div>
              <div className="text-xs text-slate-400 border-t border-slate-100 pt-3">3 deal breakers detected — deck needs major revision</div>
            </motion.div>
          </div>
        </section>

        {/* WHAT YOU GET */}
        <section className="py-20 px-6 max-w-7xl mx-auto border-t border-slate-200">
          <div className="text-center mb-14">
            <h2 className="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Everything in your analysis</h2>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 max-w-5xl mx-auto">
            {[
              { icon: AlertTriangle, title: "Deal Breakers", desc: "Top 3 reasons a VC would pass on your startup." },
              { icon: Scale, title: "Bull vs Bear Debate", desc: "AI agents argue for and against your investment case." },
              { icon: Activity, title: "Investor Readiness Score", desc: "Quantitative 0-10 score with percentile ranking." },
              { icon: Sparkles, title: "VC First Impression Sim", desc: "Watch how investors react to your deck slide-by-slide." },
              { icon: Shield, title: "Tough Investor Questions", desc: "The exact questions VCs will ask in your meeting." },
              { icon: Zap, title: "Financial Intelligence", desc: "CAC/ACV, NRR, payback — computed, not guessed." },
            ].map((f, i) => (
              <motion.div key={i} initial={{ opacity: 0, y: 20 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.05 }}
                className="p-6 rounded-2xl bg-white border border-slate-200 shadow-sm hover:border-indigo-300 transition-colors group">
                <div className="w-10 h-10 rounded-lg bg-indigo-50 text-indigo-600 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform">
                  <f.icon className="w-5 h-5" />
                </div>
                <h3 className="text-lg font-semibold text-slate-900 mb-1">{f.title}</h3>
                <p className="text-slate-600 text-sm leading-relaxed">{f.desc}</p>
              </motion.div>
            ))}
          </div>
        </section>

        {/* HOW IT WORKS — simple */}
        <section className="py-20 px-6 max-w-5xl mx-auto border-t border-slate-200">
          <div className="flex flex-col md:flex-row gap-16 items-center">
            <div className="flex-1 space-y-8">
              <h2 className="text-3xl md:text-4xl font-bold text-slate-900">30 seconds. Full VC memo.</h2>
              <div className="space-y-6">
                {[
                  { num: "01", title: "Upload your pitch deck PDF", desc: "We parse every slide, table, and data point." },
                  { num: "02", title: "AI researches your market live", desc: "Web search validates claims, finds competitors, checks metrics." },
                  { num: "03", title: "Agents debate your investment case", desc: "Bull and bear analysts argue. A judge scores you." },
                  { num: "04", title: "Get your full investment memo", desc: "Score, deal breakers, slide fixes, investor questions — all in one." }
                ].map((step, i) => (
                  <div key={i} className="flex gap-4">
                    <div className="flex-shrink-0 w-10 h-10 rounded-full bg-indigo-50 border border-indigo-200 flex items-center justify-center text-sm font-bold text-indigo-600">{step.num}</div>
                    <div>
                      <h4 className="text-lg font-semibold text-slate-900">{step.title}</h4>
                      <p className="text-slate-600 text-sm">{step.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
            <div className="flex-1 w-full">
              <div className="aspect-[4/3] rounded-2xl bg-white border border-slate-200 p-8 relative overflow-hidden flex items-center justify-center shadow-lg">
                <div className="absolute inset-0 bg-[linear-gradient(to_right,#e2e8f020_1px,transparent_1px),linear-gradient(to_bottom,#e2e8f020_1px,transparent_1px)] bg-[size:14px_24px]" />
                <motion.div animate={{ boxShadow: ["0 0 0 0 rgba(79,70,229,0)", "0 0 0 20px rgba(79,70,229,0.1)", "0 0 0 40px rgba(79,70,229,0)"] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="relative z-10 w-24 h-24 rounded-2xl bg-indigo-600 flex items-center justify-center shadow-lg shadow-indigo-500/30">
                  <Search className="w-10 h-10 text-white" />
                </motion.div>
              </div>
            </div>
          </div>
        </section>

        {/* FINAL CTA */}
        <section className="py-24 px-6 max-w-4xl mx-auto text-center border-t border-slate-200">
          <h2 className="text-4xl md:text-5xl font-bold text-slate-900 mb-6">
            Find out if investors will reject your startup.
          </h2>
          <p className="text-xl text-slate-600 mb-10">
            Stop guessing. Get the exact score, deal breakers, and fixes — in 30 seconds.
          </p>
          <button onClick={handleCTA}
            className="px-10 py-4 rounded-xl bg-indigo-600 text-white font-semibold text-lg hover:bg-indigo-500 transition-all shadow-lg shadow-indigo-500/20 cursor-pointer">
            Analyze My Deck Free
          </button>
          <p className="text-sm text-slate-500 mt-4">3 free analyses. No credit card.</p>
        </section>

        <footer className="py-8 border-t border-slate-200 text-center text-slate-500 text-sm">
          <p>© {new Date().getFullYear()} Venture Intelligence Engine. All rights reserved.</p>
        </footer>
      </div>
    </div>
  );
}
