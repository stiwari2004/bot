"use client";

import React, { useState, useEffect } from "react";
import { createPortal } from "react-dom";
import { XMarkIcon, CheckCircleIcon, ExclamationTriangleIcon } from "@heroicons/react/24/outline";

interface InputExtractionModalProps {
  runbookId: number;
  ticketId: number;
  onComplete: (inputs: Record<string, any>) => void;
  onCancel: () => void;
}

interface ExtractionResult {
  extracted: Record<string, any>;
  missing: string[];
  confidence: Record<string, number>;
  source?: string;
  ticket_id?: number;
  error?: string;
}

interface LearningResult {
  learned_mappings: Array<{
    input_name: string;
    source: string;
    metadata_path: string;
    confidence: number;
  }>;
  flags: Array<{
    input_name: string;
    suggested_path: string;
    reason: string;
    confidence: number;
  }>;
  total_learned: number;
}

export function InputExtractionModal({
  runbookId,
  ticketId,
  onComplete,
  onCancel,
}: InputExtractionModalProps) {
  const [loading, setLoading] = useState(true);
  const [extracting, setExtracting] = useState(false);
  const [learning, setLearning] = useState(false);
  const [result, setResult] = useState<ExtractionResult | null>(null);
  const [userInputs, setUserInputs] = useState<Record<string, any>>({});
  const [error, setError] = useState<string | null>(null);
  const [learned, setLearned] = useState<LearningResult | null>(null);

  useEffect(() => {
    // Auto-extract on mount
    extractInputs();
  }, [runbookId, ticketId]);

  const extractInputs = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await fetch(
        `/api/v1/runbooks/demo/${runbookId}/extract-inputs?ticket_id=${ticketId}`
      );

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: "Failed to extract inputs" }));
        throw new Error(errorData.detail || "Failed to extract inputs");
      }

      const data: ExtractionResult = await response.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to extract inputs");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async () => {
    if (!result) return;

    // Check if all required inputs are provided
    const allInputs = { ...result.extracted, ...userInputs };
    const missing = result.missing.filter((name) => !allInputs[name]);

    if (missing.length > 0) {
      setError(`Please provide the following required inputs: ${missing.join(", ")}`);
      return;
    }

    setLearning(true);
    setError(null);

    try {
      // Learn from user inputs if any were provided
      if (Object.keys(userInputs).length > 0) {
        const learnResponse = await fetch(
          `/api/v1/runbooks/demo/${runbookId}/learn-inputs?ticket_id=${ticketId}`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ inputs: userInputs }),
          }
        );

        if (learnResponse.ok) {
          const learnData: LearningResult = await learnResponse.json();
          setLearned(learnData);
        }
      }

      // Complete with all inputs
      onComplete(allInputs);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to learn from inputs");
    } finally {
      setLearning(false);
    }
  };

  const getConfidenceColor = (confidence: number) => {
    if (confidence >= 0.8) return "text-green-600";
    if (confidence >= 0.6) return "text-yellow-600";
    return "text-red-600";
  };

  const getConfidenceLabel = (confidence: number) => {
    if (confidence >= 0.8) return "High";
    if (confidence >= 0.6) return "Medium";
    return "Low";
  };

  if (!result && loading) {
    return createPortal(
      <div className="fixed inset-0 z-[9999] overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
          <div className="flex items-center justify-center py-8">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <span className="ml-3 text-gray-600">Extracting inputs from ticket metadata...</span>
          </div>
        </div>
      </div>,
      document.body
    );
  }

  if (error && !result) {
    return createPortal(
      <div className="fixed inset-0 z-[9999] overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
        <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-gray-900">Input Extraction Error</h2>
            <button
              onClick={onCancel}
              className="text-gray-400 hover:text-gray-600"
            >
              <XMarkIcon className="h-6 w-6" />
            </button>
          </div>
          <div className="text-red-600 mb-4">{error}</div>
          <div className="flex justify-end gap-2">
            <button
              onClick={onCancel}
              className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            >
              Cancel
            </button>
            <button
              onClick={extractInputs}
              className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700"
            >
              Retry
            </button>
          </div>
        </div>
      </div>,
      document.body
    );
  }

  if (!result) return null;

  const allInputs = { ...result.extracted, ...userInputs };
  const hasMissing = result.missing.length > 0;
  const hasExtracted = Object.keys(result.extracted).length > 0;

  return createPortal(
    <div className="fixed inset-0 z-[9999] overflow-y-auto bg-black/60 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full p-6 max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-2xl font-semibold text-gray-900">Runbook Inputs</h2>
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="h-6 w-6" />
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700">
            {error}
          </div>
        )}

        {learned && learned.total_learned > 0 && (
          <div className="mb-4 p-3 bg-green-50 border border-green-200 rounded-lg">
            <div className="flex items-center gap-2 text-green-700">
              <CheckCircleIcon className="h-5 w-5" />
              <span className="font-medium">
                Learned {learned.total_learned} new mapping(s) from your input!
              </span>
            </div>
          </div>
        )}

        {/* Auto-extracted inputs */}
        {hasExtracted && (
          <div className="mb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-3 flex items-center gap-2">
              <CheckCircleIcon className="h-5 w-5 text-green-600" />
              Auto-extracted from ticket metadata
            </h3>
            <div className="space-y-3">
              {Object.entries(result.extracted).map(([key, value]) => (
                <div key={key} className="flex items-center gap-3">
                  <div className="flex-1">
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      {key}
                    </label>
                    <input
                      type="text"
                      value={value || ""}
                      readOnly
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg bg-gray-50 text-gray-700"
                    />
                  </div>
                  {result.confidence[key] !== undefined && (
                    <div className="flex flex-col items-end">
                      <span className={`text-xs font-medium ${getConfidenceColor(result.confidence[key])}`}>
                        {getConfidenceLabel(result.confidence[key])}
                      </span>
                      <span className="text-xs text-gray-500">
                        {(result.confidence[key] * 100).toFixed(0)}%
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Missing inputs for user entry */}
        {hasMissing && (
          <div className="mb-6">
            <h3 className="text-lg font-medium text-gray-900 mb-3 flex items-center gap-2">
              <ExclamationTriangleIcon className="h-5 w-5 text-yellow-600" />
              Please provide the following inputs
            </h3>
            <div className="space-y-3">
              {result.missing.map((inputName) => (
                <div key={inputName}>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    {inputName} <span className="text-red-600">*</span>
                  </label>
                  <input
                    type="text"
                    value={userInputs[inputName] || ""}
                    onChange={(e) =>
                      setUserInputs({
                        ...userInputs,
                        [inputName]: e.target.value,
                      })
                    }
                    placeholder={`Enter ${inputName}`}
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    required
                  />
                </div>
              ))}
            </div>
          </div>
        )}

        {!hasMissing && !hasExtracted && (
          <div className="mb-6 p-4 bg-gray-50 rounded-lg text-gray-600 text-center">
            No inputs required for this runbook.
          </div>
        )}

        {/* Action buttons */}
        <div className="flex justify-end gap-3 pt-4 border-t">
          <button
            onClick={onCancel}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200"
            disabled={learning}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={learning || (hasMissing && result.missing.some((name) => !userInputs[name]))}
            className="px-4 py-2 text-white bg-blue-600 rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {learning ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
                Learning...
              </>
            ) : (
              "Continue"
            )}
          </button>
        </div>
      </div>
    </div>,
    document.body
  );
}




