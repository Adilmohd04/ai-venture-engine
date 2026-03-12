import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

export default function ImprovementTracker({ history, currentAnalysisId }) {
  if (!history || history.length < 2) return null;

  const sorted = [...history].sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  const currentIndex = sorted.findIndex(h => h.analysis_id === currentAnalysisId);
  const current = sorted[currentIndex];
  const previous = currentIndex > 0 ? sorted[currentIndex - 1] : null;

  if (!previous) return null;

  const scoreDiff = current.final_score - previous.final_score;
  const percentChange = ((scoreDiff / previous.final_score) * 100).toFixed(1);

  const getTrendIcon = () => {
    if (scoreDiff > 0.5) return <TrendingUp className="text-emerald-500" size={24} />;
    if (scoreDiff < -0.5) return <TrendingDown className="text-rose-500" size={24} />;
    return <Minus className="text-amber-500" size={24} />;
  };

  const getTrendColor = () => {
    if (scoreDiff > 0.5) return 'from-emerald-50 to-green-50 border-emerald-200';
    if (scoreDiff < -0.5) return 'from-rose-50 to-red-50 border-rose-200';
    return 'from-amber-50 to-orange-50 border-amber-200';
  };

  const getTrendText = () => {
    if (scoreDiff > 0.5) return 'Improved';
    if (scoreDiff < -0.5) return 'Declined';
    return 'Stable';
  };

  return (
    <div className={`bg-gradient-to-r ${getTrendColor()} border rounded-xl p-6 mb-6`}>
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-lg font-semibold text-slate-900 mb-1">📊 Deck Improvement Tracker</h3>
          <p className="text-sm text-slate-600">
            Comparing to previous analysis from {new Date(previous.created_at).toLocaleDateString()}
          </p>
        </div>
        {getTrendIcon()}
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="bg-white border border-slate-200 rounded-lg p-4 text-center shadow-sm">
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Previous</div>
          <div className="text-3xl font-bold text-slate-600">{previous.final_score.toFixed(1)}</div>
          <div className="text-xs text-slate-500 mt-1">{previous.verdict}</div>
        </div>

        <div className="bg-white border border-slate-200 rounded-lg p-4 text-center shadow-sm">
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Change</div>
          <div className={`text-3xl font-bold ${
            scoreDiff > 0 ? 'text-emerald-600' : scoreDiff < 0 ? 'text-rose-600' : 'text-amber-600'
          }`}>
            {scoreDiff > 0 ? '+' : ''}{scoreDiff.toFixed(1)}
          </div>
          <div className={`text-xs mt-1 ${
            scoreDiff > 0 ? 'text-emerald-500' : scoreDiff < 0 ? 'text-rose-500' : 'text-amber-500'
          }`}>
            {scoreDiff > 0 ? '+' : ''}{percentChange}%
          </div>
        </div>

        <div className="bg-white border-2 border-indigo-300 rounded-lg p-4 text-center shadow-sm">
          <div className="text-xs text-indigo-500 uppercase tracking-wider mb-1">Current</div>
          <div className="text-3xl font-bold text-slate-900">{current.final_score.toFixed(1)}</div>
          <div className="text-xs text-indigo-500 mt-1">{current.verdict}</div>
        </div>
      </div>

      {/* Progress Bar */}
      <div className="relative">
        <div className="h-2 bg-slate-100 rounded-full overflow-hidden border border-slate-200">
          <div
            className={`h-full transition-all duration-1000 ${
              scoreDiff > 0 ? 'bg-gradient-to-r from-emerald-500 to-green-400' :
              scoreDiff < 0 ? 'bg-gradient-to-r from-rose-500 to-red-400' :
              'bg-gradient-to-r from-amber-500 to-orange-400'
            }`}
            style={{ width: `${(current.final_score / 10) * 100}%` }}
          />
        </div>
        <div className="flex justify-between mt-2 text-xs text-slate-400">
          <span>0</span>
          <span className="font-semibold text-slate-700">{getTrendText()}</span>
          <span>10</span>
        </div>
      </div>

      {/* Timeline */}
      {sorted.length > 2 && (
        <div className="mt-6 pt-4 border-t border-slate-200">
          <div className="text-xs text-slate-500 mb-3">Score History</div>
          <div className="flex items-end gap-2 h-20">
            {sorted.map((h, i) => {
              const height = Math.max(10, (h.final_score / 10) * 100);
              const isCurrent = h.analysis_id === currentAnalysisId;
              return (
                <div key={i} className="flex flex-col items-center flex-1 gap-1">
                  <span className={`text-xs font-mono ${isCurrent ? 'text-indigo-600 font-bold' : 'text-slate-500'}`}>
                    {h.final_score.toFixed(1)}
                  </span>
                  <div
                    className={`w-full rounded-t transition-all ${
                      isCurrent ? 'bg-indigo-500' : 'bg-slate-200 hover:bg-slate-300'
                    }`}
                    style={{ height: `${height}%` }}
                  />
                  <span className="text-[10px] text-slate-500">
                    {new Date(h.created_at).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Insights */}
      {scoreDiff > 0.5 && (
        <div className="mt-4 bg-emerald-50 border border-emerald-200 rounded-lg p-3">
          <div className="text-sm text-emerald-700 font-semibold mb-1">🎉 Great Progress!</div>
          <div className="text-xs text-slate-600">
            Your deck improved by {Math.abs(scoreDiff).toFixed(1)} points. Keep refining based on the feedback above.
          </div>
        </div>
      )}

      {scoreDiff < -0.5 && (
        <div className="mt-4 bg-rose-50 border border-rose-200 rounded-lg p-3">
          <div className="text-sm text-rose-700 font-semibold mb-1">⚠️ Score Declined</div>
          <div className="text-xs text-slate-600">
            Review the slide-by-slide feedback and deal breakers to identify areas for improvement.
          </div>
        </div>
      )}
    </div>
  );
}
