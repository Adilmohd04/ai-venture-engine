import { Zap } from "lucide-react";

export default function PriorityBadge() {
  return (
    <span className="bg-amber-50 border border-amber-200 text-amber-700 rounded-full px-3 py-1 text-xs font-semibold inline-flex items-center gap-1">
      <Zap size={12} />
      Priority Processing
    </span>
  );
}
