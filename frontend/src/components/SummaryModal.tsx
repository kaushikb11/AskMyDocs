import { useState } from "react";
import {
  FileText,
  Clock,
  Hash,
  Target,
  AlertCircle,
  CheckCircle,
  Loader2,
} from "lucide-react";
import { Modal } from "./ui/modal";
import { Button } from "./ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import {
  generateSummary,
  type SummaryType,
  type SummaryResponse,
} from "../lib/api";
import { COLORS, TYPOGRAPHY } from "../lib/design-system";

interface SummaryModalProps {
  isOpen: boolean;
  onClose: () => void;
  documentId: string;
  documentName: string;
}

interface SummaryOptions {
  summaryType: SummaryType;
  includeKeyPoints: boolean;
  includeTablesSummary: boolean;
  includeFiguresSummary: boolean;
  customInstructions: string;
}

export function SummaryModal({
  isOpen,
  onClose,
  documentId,
  documentName,
}: SummaryModalProps) {
  const [options, setOptions] = useState<SummaryOptions>({
    summaryType: "brief",
    includeKeyPoints: true,
    includeTablesSummary: true,
    includeFiguresSummary: true,
    customInstructions: "",
  });

  const [isGenerating, setIsGenerating] = useState(false);
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const summaryTypeOptions = [
    {
      value: "brief",
      label: "Brief",
      description: "Quick overview in 1-2 paragraphs",
    },
    {
      value: "detailed",
      label: "Detailed",
      description: "Comprehensive summary in 3-5 paragraphs",
    },
    {
      value: "bullet_points",
      label: "Bullet Points",
      description: "Key points in structured format",
    },
    {
      value: "executive",
      label: "Executive",
      description: "Business-focused executive summary",
    },
  ];

  const handleGenerateSummary = async () => {
    setIsGenerating(true);
    setError(null);
    setSummary(null);

    try {
      const result = await generateSummary({
        document_id: documentId,
        summary_type: options.summaryType,
        custom_instructions: options.customInstructions || undefined,
        include_key_points: options.includeKeyPoints,
        include_tables_summary: options.includeTablesSummary,
        include_figures_summary: options.includeFiguresSummary,
      });

      setSummary(result);
    } catch (err) {
      console.error("Summary generation failed:", err);
      setError(
        err instanceof Error ? err.message : "Failed to generate summary",
      );
    } finally {
      setIsGenerating(false);
    }
  };

  const handleClose = () => {
    setSummary(null);
    setError(null);
    setIsGenerating(false);
    onClose();
  };

  const formatGenerationTime = (seconds: number) => {
    return seconds < 1 ? "< 1s" : `${seconds.toFixed(1)}s`;
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={handleClose}
      title={`Document Summary - ${documentName}`}
      size="lg"
    >
      <div className="p-6">
        {!summary && !isGenerating && (
          <div className="space-y-6">
            {/* Summary Type Selection */}
            <div>
              <label
                className={`block ${TYPOGRAPHY.body.default} font-medium ${COLORS.text.primary} mb-3`}
              >
                Summary Type
              </label>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {summaryTypeOptions.map((option) => (
                  <div
                    key={option.value}
                    className={`p-4 border rounded-lg cursor-pointer transition-all ${
                      options.summaryType === option.value
                        ? "border-blue-500 bg-blue-50"
                        : "border-gray-200 hover:border-gray-300"
                    }`}
                    onClick={() =>
                      setOptions({
                        ...options,
                        summaryType: option.value as SummaryType,
                      })
                    }
                  >
                    <div className={`font-medium ${COLORS.text.primary} mb-1`}>
                      {option.label}
                    </div>
                    <div
                      className={`${TYPOGRAPHY.body.small} ${COLORS.text.secondary}`}
                    >
                      {option.description}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Include Options */}
            <div>
              <label
                className={`block ${TYPOGRAPHY.body.default} font-medium ${COLORS.text.primary} mb-3`}
              >
                Include Additional Content
              </label>
              <div className="space-y-2">
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={options.includeKeyPoints}
                    onChange={(e) =>
                      setOptions({
                        ...options,
                        includeKeyPoints: e.target.checked,
                      })
                    }
                    className="h-4 w-4 text-blue-600 rounded border-gray-300"
                  />
                  <span
                    className={`${TYPOGRAPHY.body.default} ${COLORS.text.primary}`}
                  >
                    Key Points
                  </span>
                </label>
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={options.includeTablesSummary}
                    onChange={(e) =>
                      setOptions({
                        ...options,
                        includeTablesSummary: e.target.checked,
                      })
                    }
                    className="h-4 w-4 text-blue-600 rounded border-gray-300"
                  />
                  <span
                    className={`${TYPOGRAPHY.body.default} ${COLORS.text.primary}`}
                  >
                    Tables Summary
                  </span>
                </label>
                <label className="flex items-center space-x-3">
                  <input
                    type="checkbox"
                    checked={options.includeFiguresSummary}
                    onChange={(e) =>
                      setOptions({
                        ...options,
                        includeFiguresSummary: e.target.checked,
                      })
                    }
                    className="h-4 w-4 text-blue-600 rounded border-gray-300"
                  />
                  <span
                    className={`${TYPOGRAPHY.body.default} ${COLORS.text.primary}`}
                  >
                    Figures Summary
                  </span>
                </label>
              </div>
            </div>

            {/* Custom Instructions */}
            <div>
              <label
                className={`block ${TYPOGRAPHY.body.default} font-medium ${COLORS.text.primary} mb-2`}
              >
                Custom Instructions (Optional)
              </label>
              <textarea
                value={options.customInstructions}
                onChange={(e) =>
                  setOptions({ ...options, customInstructions: e.target.value })
                }
                placeholder="Add any specific instructions for the summary generation..."
                className={`w-full p-3 border border-gray-300 rounded-lg ${TYPOGRAPHY.body.default} resize-none`}
                rows={3}
              />
            </div>

            {/* Generate Button */}
            <div className="flex justify-end space-x-3">
              <Button variant="outline" onClick={handleClose}>
                Cancel
              </Button>
              <Button onClick={handleGenerateSummary} disabled={isGenerating}>
                <FileText className="h-4 w-4 mr-2" />
                Generate Summary
              </Button>
            </div>
          </div>
        )}

        {/* Loading State */}
        {isGenerating && (
          <div className="flex flex-col items-center justify-center py-12">
            <Loader2
              className={`h-8 w-8 animate-spin ${COLORS.status.info} mb-4`}
            />
            <h3
              className={`${TYPOGRAPHY.heading.h4} ${COLORS.text.primary} mb-2`}
            >
              Generating Summary
            </h3>
            <p
              className={`${COLORS.text.secondary} ${TYPOGRAPHY.body.default} text-center`}
            >
              Analyzing document content and creating your {options.summaryType}{" "}
              summary...
            </p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="flex flex-col items-center justify-center py-12">
            <AlertCircle className={`h-8 w-8 ${COLORS.status.error} mb-4`} />
            <h3
              className={`${TYPOGRAPHY.heading.h4} ${COLORS.status.error} mb-2`}
            >
              Summary Generation Failed
            </h3>
            <p
              className={`${COLORS.text.secondary} ${TYPOGRAPHY.body.default} text-center mb-6`}
            >
              {error}
            </p>
            <div className="flex space-x-3">
              <Button variant="outline" onClick={handleClose}>
                Close
              </Button>
              <Button onClick={handleGenerateSummary}>Try Again</Button>
            </div>
          </div>
        )}

        {/* Summary Display */}
        {summary && (
          <div className="space-y-6">
            {/* Summary Header */}
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <CheckCircle className={`h-5 w-5 ${COLORS.status.success}`} />
                <h3
                  className={`${TYPOGRAPHY.heading.h4} ${COLORS.text.primary}`}
                >
                  Summary Generated
                </h3>
              </div>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <div className="flex items-center space-x-1">
                  <Clock className="h-4 w-4" />
                  <span>{formatGenerationTime(summary.generation_time)}</span>
                </div>
                {summary.tokens_used && (
                  <div className="flex items-center space-x-1">
                    <Hash className="h-4 w-4" />
                    <span>{summary.tokens_used} tokens</span>
                  </div>
                )}
                <div className="flex items-center space-x-1">
                  <Target className="h-4 w-4" />
                  <span>{summary.summary_type}</span>
                </div>
              </div>
            </div>

            {/* Main Summary */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center space-x-2">
                  <FileText className="h-5 w-5" />
                  <span>{summary.title || "Document Summary"}</span>
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div
                  className={`${TYPOGRAPHY.body.default} ${COLORS.text.primary} whitespace-pre-wrap leading-relaxed`}
                >
                  {summary.overview}
                </div>
              </CardContent>
            </Card>

            {/* Key Points */}
            {summary.key_points && summary.key_points.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Key Points</CardTitle>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2">
                    {summary.key_points.map((point, index) => (
                      <li
                        key={index}
                        className={`flex items-start space-x-2 ${TYPOGRAPHY.body.default}`}
                      >
                        <span className="text-blue-500 mt-1">•</span>
                        <span>{point}</span>
                      </li>
                    ))}
                  </ul>
                </CardContent>
              </Card>
            )}

            {/* Tables Summary */}
            {summary.tables_summary && (
              <Card>
                <CardHeader>
                  <CardTitle>Tables Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div
                    className={`${TYPOGRAPHY.body.default} ${COLORS.text.primary} whitespace-pre-wrap`}
                  >
                    {summary.tables_summary}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Figures Summary */}
            {summary.figures_summary && (
              <Card>
                <CardHeader>
                  <CardTitle>Figures Summary</CardTitle>
                </CardHeader>
                <CardContent>
                  <div
                    className={`${TYPOGRAPHY.body.default} ${COLORS.text.primary} whitespace-pre-wrap`}
                  >
                    {summary.figures_summary}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Action Buttons */}
            <div className="flex justify-end space-x-3">
              <Button
                variant="outline"
                onClick={() => {
                  setSummary(null);
                  setError(null);
                }}
              >
                Generate New Summary
              </Button>
              <Button onClick={handleClose}>Close</Button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}
