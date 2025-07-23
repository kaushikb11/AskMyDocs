import { useState, useEffect } from "react";
import {
  getDocuments,
  formatFileSize,
  formatUploadTime,
  APIError,
  type DocumentListItem,
} from "../lib/api";

export interface Document {
  id: string;
  name: string;
  size: string;
  status: "pending" | "processing" | "completed" | "failed";
  uploadTime: string;
  pages: number;
  tables: number;
  figures: number;
}

interface UseDocumentsReturn {
  documents: Document[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function useDocuments(): UseDocumentsReturn {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = async () => {
    setLoading(true);
    setError(null);

    try {
      const response = await getDocuments();

      // Transform API response to expected format
      const transformedDocs: Document[] = response.documents.map(
        (doc: DocumentListItem) => ({
          id: doc.document_id,
          name: doc.filename,
          size: formatFileSize(doc.file_size),
          status: doc.status === "failed" ? "failed" : doc.status,
          uploadTime: formatUploadTime(doc.upload_time),
          pages: doc.page_count || 0,
          tables: doc.tables_count || 0,
          figures: doc.figures_count || 0,
        }),
      );

      setDocuments(transformedDocs);
    } catch (err) {
      if (err instanceof APIError) {
        setError(err.message);
      } else {
        setError("Failed to load documents");
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  return {
    documents,
    loading,
    error,
    refetch: fetchDocuments,
  };
}
