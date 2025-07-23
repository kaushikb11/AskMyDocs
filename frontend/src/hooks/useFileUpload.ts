import { useState, useCallback } from "react";
import { APP_CONFIG, UI_MESSAGES } from "../lib/constants";
import { uploadDocument, APIError } from "../lib/api";

interface UseFileUploadReturn {
  selectedFile: File | null;
  uploading: boolean;
  uploaded: boolean;
  error: string | null;
  selectFile: (file: File) => void;
  uploadFile: () => Promise<void>;
  resetUpload: () => void;
}

export function useFileUpload(
  onUploadSuccess?: () => void,
): UseFileUploadReturn {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploaded, setUploaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const validateFile = useCallback((file: File): string | null => {
    // Check file size
    if (file.size > APP_CONFIG.maxFileSize) {
      return UI_MESSAGES.errors.fileTooBig;
    }

    // Check file type
    const fileExtension = "." + file.name.split(".").pop()?.toLowerCase();
    if (!APP_CONFIG.supportedFileTypes.includes(fileExtension as ".pdf")) {
      return UI_MESSAGES.errors.invalidFormat;
    }

    return null;
  }, []);

  const selectFile = useCallback(
    (file: File) => {
      const validationError = validateFile(file);
      if (validationError) {
        setError(validationError);
        setSelectedFile(null);
      } else {
        setError(null);
        setSelectedFile(file);
        setUploaded(false);
      }
    },
    [validateFile],
  );

  const uploadFile = useCallback(async () => {
    if (!selectedFile) return;

    setUploading(true);
    setError(null);

    try {
      await uploadDocument(selectedFile);

      setUploaded(true);
      onUploadSuccess?.();

      // Auto-reset after success message
      setTimeout(() => {
        setSelectedFile(null);
        setUploaded(false);
      }, 2000);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError(
          err instanceof Error ? err.message : UI_MESSAGES.errors.uploadFailed,
        );
      }
    } finally {
      setUploading(false);
    }
  }, [selectedFile, onUploadSuccess]);

  const resetUpload = useCallback(() => {
    setSelectedFile(null);
    setUploading(false);
    setUploaded(false);
    setError(null);
  }, []);

  return {
    selectedFile,
    uploading,
    uploaded,
    error,
    selectFile,
    uploadFile,
    resetUpload,
  };
}
