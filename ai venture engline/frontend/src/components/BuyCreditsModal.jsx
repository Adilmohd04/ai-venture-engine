import { useState } from 'react';
import { X, Zap, Check } from 'lucide-react';

const PACKAGES = [
  { id: '10_credits', credits: 10, price: 29, popular: false },
  { id: '25_credits', credits: 25, price: 59, popular: true, savings: '19%' },
  { id: '50_credits', credits: 50, price: 99, popular: false, savings: '32%' },
];

export default function BuyCreditsModal({ isOpen, onClose }) {
  const [loading, setLoading] = useState(false);
  const [selectedPackage, setSelectedPackage] = useState('25_credits');

  if (!isOpen) return null;

  const handlePurchase = async () => {
    setLoading(true);
    try {
      const token = localStorage.getItem('supabase_token');
      const response = await fetch('/api/create-checkout-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ package_id: selectedPackage }),
      });

      if (!response.ok) {
        throw new Error('Failed to create checkout session');
      }

      const data = await response.json();
      window.location.href = data.checkout_url;
    } catch (error) {
      console.error('Purchase error:', error);
      alert('Failed to start checkout. Please try again.');
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
      <div className="bg-white border border-slate-200 rounded-2xl max-w-3xl w-full p-8 relative">
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-slate-9000 hover:text-slate-900 transition"
        >
          <X size={24} />
        </button>

        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-blue-600/20 rounded-full mb-4">
            <Zap className="text-blue-400" size={32} />
          </div>
          <h2 className="text-3xl font-bold text-slate-900 mb-2">Buy Analysis Credits</h2>
          <p className="text-slate-600">
            Choose a package and continue analyzing pitch decks
          </p>
        </div>

        {/* Packages */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {PACKAGES.map((pkg) => (
            <button
              key={pkg.id}
              onClick={() => setSelectedPackage(pkg.id)}
              className={`relative p-6 rounded-xl border-2 transition-all ${
                selectedPackage === pkg.id
                  ? 'border-blue-600 bg-blue-600/10'
                  : 'border-slate-200 bg-white shadow-sm hover:border-slate-300'
              }`}
            >
              {pkg.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-1 bg-blue-600 text-slate-900 text-xs font-semibold rounded-full">
                  Most Popular
                </div>
              )}

              <div className="text-center">
                <div className="text-4xl font-bold text-slate-900 mb-2">
                  {pkg.credits}
                </div>
                <div className="text-sm text-slate-9000 mb-4">Credits</div>

                <div className="text-3xl font-bold text-slate-900 mb-1">
                  ${pkg.price}
                </div>
                <div className="text-sm text-slate-9000 mb-4">
                  ${(pkg.price / pkg.credits).toFixed(2)} per credit
                </div>

                {pkg.savings && (
                  <div className="inline-block px-3 py-1 bg-green-600/20 text-green-400 text-xs font-semibold rounded-full">
                    Save {pkg.savings}
                  </div>
                )}

                {selectedPackage === pkg.id && (
                  <div className="mt-4 flex items-center justify-center gap-2 text-blue-400">
                    <Check size={20} />
                    <span className="text-sm font-semibold">Selected</span>
                  </div>
                )}
              </div>
            </button>
          ))}
        </div>

        {/* Features */}
        <div className="bg-slate-50/50 rounded-xl p-6 mb-8">
          <h3 className="text-lg font-semibold text-slate-900 mb-4">What you get:</h3>
          <ul className="space-y-3">
            {[
              'Full AI-powered pitch deck analysis',
              'Investment memo with bull/bear debate',
              'Slide-by-slide feedback',
              'Deal breaker detection',
              'Investor questions generator',
              'Shareable public reports',
            ].map((feature, i) => (
              <li key={i} className="flex items-center gap-3 text-slate-700">
                <Check className="text-green-400 flex-shrink-0" size={20} />
                <span>{feature}</span>
              </li>
            ))}
          </ul>
        </div>

        {/* Purchase button */}
        <button
          onClick={handlePurchase}
          disabled={loading}
          className="w-full py-4 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-700 disabled:cursor-not-allowed text-slate-900 font-semibold rounded-xl transition"
        >
          {loading ? 'Redirecting to checkout...' : `Purchase ${PACKAGES.find(p => p.id === selectedPackage)?.credits} Credits`}
        </button>

        <p className="text-center text-xs text-slate-9000 mt-4">
          Secure payment powered by Stripe. Credits never expire.
        </p>
      </div>
    </div>
  );
}
