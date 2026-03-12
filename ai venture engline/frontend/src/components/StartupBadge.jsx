import { motion } from 'framer-motion';

const getScoreGradient = (score) => {
  if (score >= 8) return 'from-emerald-500 to-teal-600';
  if (score >= 6) return 'from-indigo-500 to-purple-600';
  if (score >= 4) return 'from-amber-500 to-orange-600';
  return 'from-rose-500 to-red-600';
};

const getScoreLabel = (score) => {
  if (score >= 8) return 'Investor Ready';
  if (score >= 6) return 'Promising';
  if (score >= 4) return 'Needs Work';
  return 'Major Gaps';
};

export default function StartupBadge({ startupName, score, percentile, totalAnalyses, shareUrl }) {
  const handleShare = () => {
    const percentileText = percentile ? `Top ${100 - percentile}% of startups analyzed.` : '';
    const text = `${startupName} scored ${score.toFixed(1)}/10 on Venture Intelligence Engine. ${percentileText}\n\nAnalyze your pitch deck free:`;
    
    if (navigator.share) {
      navigator.share({ title: text, url: shareUrl });
    } else {
      navigator.clipboard.writeText(`${text}\n${shareUrl}`);
      alert('Copied to clipboard!');
    }
  };

  const handleTweet = () => {
    const percentileText = percentile ? ` Top ${100 - percentile}% of startups analyzed by AI.` : '';
    const text = encodeURIComponent(
      `Our startup scored ${score.toFixed(1)}/10 on Venture Intelligence Engine.${percentileText}\n\nAnalyze your pitch deck free:`
    );
    const url = encodeURIComponent(shareUrl);
    window.open(`https://twitter.com/intent/tweet?text=${text}&url=${url}`, '_blank');
  };

  return (
    <div className="bg-white border border-slate-200 rounded-2xl p-6 shadow-sm">
      {/* Badge Card */}
      <div className="bg-gradient-to-br from-slate-50 to-slate-100 border border-slate-200 rounded-xl p-6 text-center mb-5">
        <div className="flex items-center justify-center gap-2 mb-1">
          <div className="w-4 h-4 bg-gradient-to-br from-indigo-500 to-purple-600 rounded flex items-center justify-center">
            <div className="w-2 h-2 border border-white rounded-sm" />
          </div>
          <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Venture Intelligence</span>
        </div>
        
        <div className="text-xs text-slate-500 font-medium mt-3 mb-1">Investor Readiness Score</div>
        
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.5, type: 'spring' }}
          className={`text-5xl font-extrabold tracking-tighter bg-gradient-to-br ${getScoreGradient(score)} bg-clip-text text-transparent`}
        >
          {score.toFixed(1)}
        </motion.div>
        
        <div className="text-xs text-slate-400 mb-2">out of 10</div>
        <div className="text-sm font-semibold text-slate-700">{getScoreLabel(score)}</div>
        
        {percentile > 0 && totalAnalyses > 5 && (
          <div className="mt-3 inline-flex items-center gap-1.5 px-3 py-1 bg-indigo-50 border border-indigo-200 rounded-full">
            <span className="text-xs font-bold text-indigo-600">Top {100 - percentile}%</span>
            <span className="text-xs text-indigo-400">of startups analyzed</span>
          </div>
        )}
      </div>

      {/* Share Buttons */}
      <div className="space-y-2">
        <button
          onClick={handleTweet}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-slate-900 text-white rounded-xl text-sm font-semibold hover:bg-slate-800 transition-colors cursor-pointer"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z"/></svg>
          Post on X
        </button>
        <button
          onClick={handleShare}
          className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-white border border-slate-200 text-slate-700 rounded-xl text-sm font-medium hover:bg-slate-50 transition-colors cursor-pointer"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" x2="15.42" y1="13.51" y2="17.49"/><line x1="15.41" x2="8.59" y1="6.51" y2="10.49"/></svg>
          Share Score
        </button>
      </div>
    </div>
  );
}
