import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../contexts/AuthContext";
import { authFetch } from "../lib/supabase";
import { motion } from "framer-motion";
import { Check, X, Shield, Zap, Sparkles } from "lucide-react";

const PAYPAL_CLIENT_ID = import.meta.env.VITE_PAYPAL_CLIENT_ID;
const API_URL = import.meta.env.VITE_API_URL || "https://ai-venture-engine.onrender.com";

export default function PricingPage() {
  const { profile, user } = useAuth();
  const navigate = useNavigate();
  const [processing, setProcessing] = useState(null);
  const [paypalLoaded, setPaypalLoaded] = useState(false);

  // Load PayPal SDK
  useEffect(() => {
    if (window.paypal) {
      setPaypalLoaded(true);
      return;
    }

    const script = document.createElement("script");
    script.src = `https://www.paypal.com/sdk/js?client-id=${PAYPAL_CLIENT_ID}`;
    script.addEventListener("load", () => setPaypalLoaded(true));
    document.body.appendChild(script);
  }, []);

  const handlePayPalPayment = async (packageId) => {
    if (!user) {
      alert("Please log in to purchase credits");
      return;
    }

    setProcessing(packageId);

    try {
      // Create order on backend using authFetch (handles token automatically)
      const response = await authFetch("/api/paypal/create-order", {
        method: "POST",
        body: JSON.stringify({ package_id: packageId }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || "Failed to create order");
      }

      const { approval_url } = await response.json();
      
      // Redirect to PayPal
      window.location.href = approval_url;
    } catch (error) {
      console.error("Payment error:", error);
      alert(`Payment failed: ${error.message}`);
      setProcessing(null);
    }
  };

  const plans = [
    {
      name: "Free", price: "$0", period: "forever", credits: "3 analyses",
      description: "Perfect for founders testing the waters.",
      features: ["3 pitch deck analyses", "Public report sharing", "Basic investment memo", "AI agent reasoning"],
      limitations: ["No PDF export", "No slide feedback", "No improvement tracker"],
      current: profile?.plan === "free",
      cta: null,
    },
    {
      name: "Pro", price: "$9", period: "per month", credits: "50 analyses",
      description: "For active angel investors and serial founders.",
      features: ["50 analyses per month", "Full slide feedback", "Investor questions", "Deal breaker detector", "PDF export", "Improvement tracker"],
      limitations: [],
      current: profile?.plan === "pro", cta: "pro", recommended: true,
    },
    {
      name: "Business", price: "$29", period: "per month", credits: "Unlimited",
      description: "For VC funds, accelerators, and syndicates.",
      features: ["Unlimited analyses", "Priority processing", "Full history", "Team usage (coming soon)", "All Pro features"],
      limitations: [],
      current: profile?.plan === "business", cta: "business",
    },
  ];

  return (
    <div className="min-h-screen bg-slate-50 py-24 px-4 overflow-hidden relative">
      <div className="fixed inset-0 pointer-events-none z-0 flex justify-center">
        <div className="absolute top-[-10%] w-[800px] h-[400px] bg-indigo-600/10 rounded-full blur-[120px]" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[600px] h-[600px] bg-purple-600/10 rounded-full blur-[120px]" />
      </div>

      <div className="max-w-6xl mx-auto relative z-10">
        <div className="text-center mb-16">
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-50 text-indigo-600 text-sm font-medium border border-indigo-200 mb-6">
            <Sparkles className="w-4 h-4" /> Pricing Plans
          </motion.div>
          <motion.h1 initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="text-5xl font-bold text-slate-900 mb-6 tracking-tight">
            Scale your deal flow intelligence.
          </motion.h1>
          <motion.p initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="text-slate-600 text-xl max-w-2xl mx-auto">
            Get instant, VC-grade investment memos for a fraction of the cost of traditional due diligence.
          </motion.p>
          
          {profile && (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="mt-8 inline-flex items-center gap-4 bg-white border border-slate-200 px-6 py-3 rounded-2xl shadow-sm">
              <span className="flex items-center gap-2 text-sm text-slate-600">
                <span className="w-2 h-2 rounded-full bg-emerald-500" /> Current plan: <span className="text-slate-900 font-semibold capitalize">{profile.plan || "free"}</span>
              </span>
              <div className="w-px h-4 bg-slate-200" />
              <span className="text-sm text-slate-600">
                <span className="text-slate-900 font-medium">{profile.used ?? 0}</span> / {profile.limit ?? 3} credits used
              </span>
            </motion.div>
          )}
        </div>

        <div className="grid md:grid-cols-3 gap-8 max-w-5xl mx-auto items-start">
          {plans.map((plan, i) => (
            <motion.div
              initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 + (i * 0.1) }}
              key={plan.name}
              className={`relative bg-white shadow-sm backdrop-blur-xl border rounded-[2rem] p-8 flex flex-col ${
                plan.recommended
                  ? "border-indigo-500/50 shadow-[0_0_40px_-10px_rgba(79,70,229,0.3)] md:-translate-y-4 md:pb-12"
                  : "border-slate-200 mt-0"
              }`}
            >
              {plan.recommended && (
                <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-gradient-to-r from-indigo-500 to-purple-500 text-white text-xs font-bold px-4 py-1.5 rounded-full shadow-lg">
                  RECOMMENDED
                </div>
              )}

              {plan.current && (
                <div className="absolute -top-4 right-8 bg-emerald-50 border border-emerald-200 text-emerald-600 text-xs font-bold px-3 py-1 rounded-full">
                  CURRENT
                </div>
              )}

              <div className="mb-8">
                <h3 className="text-xl font-semibold text-slate-900 mb-2">{plan.name}</h3>
                <p className="text-slate-600 text-sm mb-6 min-h-[40px]">{plan.description}</p>
                <div className="flex items-baseline gap-1">
                  <span className="text-5xl font-bold tracking-tight text-slate-900">{plan.price}</span>
                  <span className="text-slate-900 font-medium">/{plan.period}</span>
                </div>
                <div className="inline-flex items-center gap-1.5 mt-4 px-3 py-1 rounded-lg bg-indigo-50 text-indigo-600 text-sm font-semibold border border-indigo-200">
                   <Zap className="w-3.5 h-3.5" /> {plan.credits}
                </div>
              </div>

              <div className="flex-1">
                <ul className="space-y-4 mb-8">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-start gap-3 text-sm">
                      <div className="mt-0.5 w-5 h-5 rounded-full bg-indigo-50 flex items-center justify-center shrink-0">
                        <Check className="w-3.5 h-3.5 text-indigo-600" />
                      </div>
                      <span className="text-slate-700">{feature}</span>
                    </li>
                  ))}
                </ul>
                <ul className="space-y-4">
                  {plan.limitations.map((limitation, idx) => (
                    <li key={idx} className="flex items-start gap-3 text-sm opacity-50">
                      <div className="mt-0.5 w-5 h-5 rounded-full bg-slate-100 flex items-center justify-center shrink-0">
                         <X className="w-3.5 h-3.5 text-slate-400" />
                      </div>
                      <span className="text-slate-500">{limitation}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="pt-6 border-t border-slate-200 mt-auto">
                {plan.cta ? (
                  <button
                    onClick={() => handlePayPalPayment(plan.cta)}
                    disabled={processing !== null || !paypalLoaded}
                    className={`w-full py-3.5 rounded-xl font-bold flex items-center justify-center transition-all shadow-sm ${
                      plan.recommended 
                        ? "bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-500/20" 
                        : "bg-slate-900 border border-slate-800 text-white hover:bg-slate-800"
                    } ${processing === plan.cta ? 'opacity-70 cursor-wait' : ''} ${!paypalLoaded ? 'opacity-50 cursor-not-allowed' : ''}`}
                  >
                    {processing === plan.cta ? (
                      <>
                        <div className="w-5 h-5 border-2 border-slate-400 border-t-white rounded-full animate-spin mr-2"/>
                        Processing...
                      </>
                    ) : !paypalLoaded ? (
                      'Loading PayPal...'
                    ) : (
                      plan.recommended ? 'Upgrade to Pro' : 'Upgrade to Business'
                    )}
                  </button>
                ) : plan.current ? (
                  <button disabled className="w-full py-3.5 bg-slate-100 text-slate-500 rounded-xl font-medium cursor-not-allowed">
                    Current Plan
                  </button>
                ) : (
                  <button disabled className="w-full py-3.5 bg-white text-slate-500 rounded-xl font-medium cursor-not-allowed border border-slate-200">
                    Included with Account
                  </button>
                )}
              </div>
            </motion.div>
          ))}
        </div>

        <div className="mt-32 max-w-3xl mx-auto pb-20">
          <div className="text-center mb-12">
            <Shield className="w-8 h-8 text-indigo-600 mx-auto mb-4" />
            <h2 className="text-3xl font-bold text-slate-900 tracking-tight">Frequently Asked Questions</h2>
          </div>
          <div className="space-y-4">
            {[
              { q: "How do credits work?", a: "Each pitch deck analysis consumes 1 credit. Free plan gives you 3 credits total to test the engine. Pro plan gives you 50 credits per month. Business plan features unlimited analyses." },
              { q: "Can I cancel anytime?", a: "Yes, you can cancel your subscription at any time directly from your dashboard. Your credits will remain active until the end of your current billing period." },
              { q: "What payment methods do you accept?", a: "We accept PayPal, credit cards, and debit cards through PayPal's secure, enterprise-grade checkout system." },
              { q: "Do unused credits roll over?", a: "No, credits reset at the start of each billing period. For high-volume users, we recommend the Business plan which provides unlimited analyses so there's no rollover needed." }
            ].map((faq, i) => (
              <motion.details 
                initial={{ opacity: 0, y: 10 }} whileInView={{ opacity: 1, y: 0 }} viewport={{ once: true }} transition={{ delay: i * 0.1 }}
                key={i} 
                className="group bg-white shadow-sm border border-slate-200 rounded-2xl p-6 [&_summary::-webkit-details-marker]:hidden"
              >
                <summary className="flex items-center justify-between text-slate-900 font-semibold cursor-pointer list-none">
                  {faq.q}
                  <span className="transition group-open:rotate-180 w-6 h-6 flex items-center justify-center rounded-full bg-slate-100">
                    <svg fill="none" height="16" shapeRendering="geometricPrecision" stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="1.5" viewBox="0 0 24 24" width="16"><path d="M6 9l6 6 6-6"></path></svg>
                  </span>
                </summary>
                <p className="text-slate-600 text-base mt-4 leading-relaxed pr-8">
                  {faq.a}
                </p>
              </motion.details>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
