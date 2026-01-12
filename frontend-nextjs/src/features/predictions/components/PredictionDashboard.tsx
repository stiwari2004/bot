'use client';

import { useState, useEffect } from 'react';
import { usePredictions } from '../hooks/usePredictions';

export function PredictionDashboard() {
  const { predictions, loading, error, refresh } = usePredictions();
  const [selectedRiskLevel, setSelectedRiskLevel] = useState<string | null>(null);

  useEffect(() => {
    refresh();
    // Refresh every 30 seconds
    const interval = setInterval(refresh, 30000);
    return () => clearInterval(interval);
  }, [refresh]);

  const filteredPredictions = selectedRiskLevel
    ? predictions?.filter(p => p.risk_level === selectedRiskLevel) || []
    : predictions || [];

  const riskLevelColors = {
    critical: 'bg-red-100 text-red-800 border-red-300',
    high: 'bg-orange-100 text-orange-800 border-orange-300',
    medium: 'bg-yellow-100 text-yellow-800 border-yellow-300',
    low: 'bg-green-100 text-green-800 border-green-300',
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h2 className="text-2xl font-bold text-gray-900">Incident Predictions</h2>
        <div className="flex gap-2">
          <button
            onClick={() => setSelectedRiskLevel(null)}
            className={`px-4 py-2 rounded-md text-sm font-medium ${
              selectedRiskLevel === null
                ? 'bg-blue-600 text-white'
                : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            All
          </button>
          {['critical', 'high', 'medium', 'low'].map(level => (
            <button
              key={level}
              onClick={() => setSelectedRiskLevel(level)}
              className={`px-4 py-2 rounded-md text-sm font-medium capitalize ${
                selectedRiskLevel === level
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {level}
            </button>
          ))}
        </div>
      </div>

      {loading && (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading predictions...</p>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-md p-4">
          <p className="text-red-800">Error: {error}</p>
        </div>
      )}

      {!loading && !error && filteredPredictions.length === 0 && (
        <div className="text-center py-8 bg-gray-50 rounded-lg">
          <p className="text-gray-600">No predictions found</p>
        </div>
      )}

      {!loading && !error && filteredPredictions.length > 0 && (
        <div className="grid gap-4">
          {filteredPredictions.map(prediction => (
            <div
              key={prediction.id}
              className={`border rounded-lg p-4 ${riskLevelColors[prediction.risk_level as keyof typeof riskLevelColors] || 'bg-gray-50'}`}
            >
              <div className="flex justify-between items-start">
                <div>
                  <h3 className="font-semibold text-lg capitalize">
                    {prediction.predicted_incident_type || 'Potential Incident'}
                  </h3>
                  <p className="text-sm mt-1">
                    Type: {prediction.prediction_type.replace('_', ' ')} | 
                    Confidence: {(prediction.confidence_score * 100).toFixed(1)}%
                  </p>
                  <p className="text-sm mt-1">
                    Time Horizon: {prediction.time_horizon_minutes} minutes
                  </p>
                </div>
                <div className="text-right">
                  <span className={`px-3 py-1 rounded-full text-xs font-semibold capitalize ${
                    riskLevelColors[prediction.risk_level as keyof typeof riskLevelColors] || 'bg-gray-200'
                  }`}>
                    {prediction.risk_level}
                  </span>
                  <p className="text-xs mt-2 text-gray-600">
                    {prediction.predicted_at ? new Date(prediction.predicted_at).toLocaleString() : ''}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

