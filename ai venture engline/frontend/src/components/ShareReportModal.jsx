import { useState } from 'react';
import { X, Copy, Check } from 'lucide-react';

export default function ShareReportModal({ analysisId, onClose }) {
  const [copied, setCopied] = useState(false);

  const shareUrl = `${window.location.origin}/report/${analysisId}`;

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(shareUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleTwitterShare = () => {
    const text = encodeURIComponent(
      'Check out our startup analysis on Venture Intelligence Engine — see the exact reasons investors would pass or invest.'
    );
    const url = encodeURIComponent(shareUrl);
    window.open(`https://twitter.com/intent/tweet?text=${text}&url=${url}`, '_blank');
  };

  const handleLinkedInShare = () => {
    const url = encodeURIComponent(shareUrl);
    window.open(`https://www.linkedin.com/sharing/share-offsite/?url=${url}`, '_blank');
  };

  return (
    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6 border border-slate-200">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-xl font-semibold text-slate-900">Share Your Report</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors cursor-pointer">
            <X size={24} />
          </button>
        </div>

        <p className="text-slate-600 text-sm mb-4">
          Share your investor readiness score and analysis publicly. Founders who share get more visibility.
        </p>

        <div className="bg-slate-50 rounded-xl p-3 mb-4 flex items-center gap-2 border border-slate-200">
          <input
            type="text"
            value={shareUrl}
            readOnly
            className="flex-1 bg-transparent text-sm text-slate-700 outline-none"
          />
          <button
            onClick={handleCopy}
            className="flex items-center gap-2 px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-500 transition-colors text-sm font-medium cursor-pointer"
          >
            {copied ? <><Check size={16} /> Copied!</> : <><Copy size={16} /> Copy</>}
          </button>
        </div>

        {copied && (
          <div className="mb-4 text-sm text-emerald-600 font-medium">Link copied to clipboard!</div>
        )}

        <div className="border-t border-slate-200 pt-4">
          <p className="text-sm text-slate-500 mb-3">Share on social media:</p>
          <div className="flex gap-3">
            <button
              onClick={handleTwitterShare}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-900 text-white rounded-xl hover:bg-slate-800 transition-colors text-sm font-medium cursor-pointer"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
              Post on X
            </button>
            <button
              onClick={handleLinkedInShare}
              className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-[#0A66C2] text-white rounded-xl hover:bg-[#004182] transition-colors text-sm font-medium cursor-pointer"
            >
              <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M20.447 20.452h-3.554v-5.569c0-1.328-.027-3.037-1.852-3.037-1.853 0-2.136 1.445-2.136 2.939v5.667H9.351V9h3.414v1.561h.046c.477-.9 1.637-1.85 3.37-1.85 3.601 0 4.267 2.37 4.267 5.455v6.286zM5.337 7.433c-1.144 0-2.063-.926-2.063-2.065 0-1.138.92-2.063 2.063-2.063 1.14 0 2.064.925 2.064 2.063 0 1.139-.925 2.065-2.064 2.065zm1.782 13.019H3.555V9h3.564v11.452zM22.225 0H1.771C.792 0 0 .774 0 1.729v20.542C0 23.227.792 24 1.771 24h20.451C23.2 24 24 23.227 24 22.271V1.729C24 .774 23.2 0 22.222 0h.003z"/></svg>
              LinkedIn
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
