import { Upload, File, CheckCircle, AlertCircle } from "lucide-react";
import { Button } from "./ui/button";
import { Card, CardContent } from "./ui/card";
import { useFileUpload } from "../hooks/useFileUpload";
import { UI_MESSAGES } from "../lib/constants";
import { COLORS, SPACING, TYPOGRAPHY } from "../lib/design-system";

interface FileUploadProps {
  onUploadSuccess?: () => void;
  className?: string;
}

export function FileUpload({ onUploadSuccess, className }: FileUploadProps) {
  const {
    selectedFile,
    uploading,
    uploaded,
    error,
    selectFile,
    uploadFile,
    resetUpload,
  } = useFileUpload(onUploadSuccess);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      selectFile(e.target.files[0]);
    }
  };

  return (
    <Card className={className}>
      <CardContent>
        {/* Error Display */}
        {error && (
          <div
            className={`mb-6 p-4 ${COLORS.background.error} ${COLORS.border.error} border rounded-lg flex items-center ${SPACING.gap.xs}`}
          >
            <AlertCircle
              className={`h-5 w-5 ${COLORS.status.error} flex-shrink-0`}
            />
            <p
              className={`${COLORS.status.error} ${TYPOGRAPHY.body.small} flex-1`}
            >
              {error}
            </p>
            <Button
              variant="ghost"
              size="sm"
              onClick={resetUpload}
              className={`${COLORS.status.error} hover:bg-red-100`}
            >
              Try Again
            </Button>
          </div>
        )}

        {!selectedFile ? (
          <div
            className={`border-2 border-dashed ${COLORS.border.default} rounded-xl p-8 text-center hover:border-gray-400 transition-colors`}
          >
            <Upload className={`h-12 w-12 ${COLORS.text.light} mx-auto mb-4`} />
            <h3
              className={`${TYPOGRAPHY.heading.h5} ${COLORS.text.primary} mb-2`}
            >
              {UI_MESSAGES.upload.title}
            </h3>
            <p
              className={`${COLORS.text.secondary} ${TYPOGRAPHY.body.small} mb-6`}
            >
              {UI_MESSAGES.upload.subtitle}
            </p>
            <input
              type="file"
              accept=".pdf"
              onChange={handleFileSelect}
              className={`block w-full ${TYPOGRAPHY.body.small} ${COLORS.text.secondary} file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold ${COLORS.primary[50]} file:text-blue-700 hover:file:bg-blue-100 cursor-pointer`}
            />
          </div>
        ) : (
          <div className={SPACING.gap.sm}>
            <div
              className={`flex items-center space-x-4 p-4 ${COLORS.border.default} border rounded-xl bg-gray-50`}
            >
              <File className="h-8 w-8 text-red-500 flex-shrink-0" />
              <div className="flex-1 min-w-0">
                <p
                  className={`${TYPOGRAPHY.body.default} font-medium truncate ${COLORS.text.primary}`}
                >
                  {selectedFile.name}
                </p>
                <p
                  className={`${TYPOGRAPHY.body.small} ${COLORS.text.secondary}`}
                >
                  {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
                </p>
              </div>
              {uploaded && (
                <CheckCircle
                  className={`h-6 w-6 ${COLORS.status.success} flex-shrink-0`}
                />
              )}
            </div>

            {uploaded ? (
              <div
                className={`text-center ${COLORS.status.success} font-medium ${TYPOGRAPHY.body.default}`}
              >
                {UI_MESSAGES.upload.success}
              </div>
            ) : (
              <div className="flex space-x-3">
                <Button
                  variant="primary"
                  onClick={uploadFile}
                  disabled={uploading}
                  className="flex-1"
                >
                  {uploading
                    ? UI_MESSAGES.upload.processing
                    : "Upload Document"}
                </Button>
                <Button
                  variant="outline"
                  onClick={resetUpload}
                  disabled={uploading}
                >
                  Cancel
                </Button>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
