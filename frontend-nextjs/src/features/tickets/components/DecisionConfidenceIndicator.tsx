'use client';

interface DecisionConfidenceIndicatorProps {
  confidence: number;
  size?: 'sm' | 'md' | 'lg';
}

export function DecisionConfidenceIndicator({ confidence, size = 'md' }: DecisionConfidenceIndicatorProps) {
  const percent = Math.round(confidence * 100);
  const sizeClasses = {
    sm: 'h-2',
    md: 'h-3',
    lg: 'h-4',
  };

  const getColor = () => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.5) return 'bg-yellow-500';
    return 'bg-red-500';
  };

  const getTextColor = () => {
    if (confidence >= 0.8) return 'text-green-700';
    if (confidence >= 0.5) return 'text-yellow-700';
    return 'text-red-700';
  };

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-gray-200 rounded-full overflow-hidden">
        <div
          className={`${getColor()} ${sizeClasses[size]} transition-all duration-300`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <span className={`text-sm font-medium ${getTextColor()}`}>{percent}%</span>
    </div>
  );
}








