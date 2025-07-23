import { useState } from "react";
import {
  FileText,
  CheckCircle,
  Eye,
  Loader2,
  AlertCircle,
  RefreshCw,
  FileSpreadsheet,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { useDocuments } from "../hooks/useDocuments";
import { UI_MESSAGES } from "../lib/constants";
import { COLORS, SPACING, TYPOGRAPHY } from "../lib/design-system";
import { SummaryModal } from "./SummaryModal";

interface DocumentListProps {
  onDocumentSelect?: (documentId: string) => void;
}

export function DocumentList({ onDocumentSelect }: DocumentListProps) {
  const { documents, loading, error, refetch } = useDocuments();
  const [summaryModal, setSummaryModal] = useState<{
    isOpen: boolean;
    documentId: string;
    documentName: string;
  }>({
    isOpen: false,
    documentId: "",
    documentName: "",
  });

  if (loading) {
    return (
      <Card>
        <CardContent className="py-16 text-center">
          <Loader2
            className={`h-8 w-8 animate-spin mx-auto mb-4 ${COLORS.status.info}`}
          />
          <p className={`${COLORS.text.secondary} ${TYPOGRAPHY.body.default}`}>
            Loading documents...
          </p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card>
        <CardContent className="py-16 text-center">
          <AlertCircle
            className={`h-8 w-8 mx-auto mb-4 ${COLORS.status.error}`}
          />
          <p
            className={`${COLORS.status.error} ${TYPOGRAPHY.body.default} mb-6`}
          >
            {error}
          </p>
          <Button onClick={refetch} variant="outline">
            <RefreshCw className="h-4 w-4 mr-2" />
            Try Again
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (documents.length === 0) {
    return (
      <Card>
        <CardContent className="py-16 text-center">
          <FileText className={`h-12 w-12 mx-auto mb-6 ${COLORS.text.light}`} />
          <h3
            className={`${TYPOGRAPHY.heading.h4} ${COLORS.text.primary} mb-3`}
          >
            No Documents
          </h3>
          <p className={`${COLORS.text.secondary} ${TYPOGRAPHY.body.default}`}>
            {UI_MESSAGES.documents.empty}
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0">
        <CardTitle className={COLORS.text.primary}>
          Documents ({documents.length})
        </CardTitle>
        <Button
          variant="ghost"
          size="sm"
          onClick={refetch}
          title="Refresh documents"
        >
          <RefreshCw className="h-4 w-4" />
        </Button>
      </CardHeader>
      <CardContent>
        <div className={SPACING.gap.sm}>
          {documents.map((doc) => (
            <Card
              key={doc.id}
              className="hover:shadow-md transition-all duration-200 border-gray-100"
            >
              <CardContent className="py-4">
                <div className="flex items-center space-x-4">
                  <FileText className="h-8 w-8 text-red-500 flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <h3
                      className={`${TYPOGRAPHY.body.default} font-medium truncate ${COLORS.text.primary} mb-1`}
                    >
                      {doc.name}
                    </h3>
                    <div
                      className={`flex items-center space-x-4 ${TYPOGRAPHY.body.small} ${COLORS.text.muted} flex-wrap gap-y-1`}
                    >
                      <span>{doc.size}</span>
                      <span>•</span>
                      <span>{doc.uploadTime}</span>
                      <span>•</span>
                      <span>{doc.pages} pages</span>
                      <span>•</span>
                      <span>{doc.tables} tables</span>
                      <span>•</span>
                      <span>{doc.figures} figures</span>
                    </div>
                  </div>
                  <div className="flex items-center space-x-3 flex-shrink-0">
                    <div className="flex items-center">
                      {doc.status === "completed" && (
                        <CheckCircle
                          className={`h-5 w-5 ${COLORS.status.success}`}
                        />
                      )}
                      {doc.status === "processing" && (
                        <Loader2
                          className={`h-5 w-5 ${COLORS.status.info} animate-spin`}
                        />
                      )}
                      {doc.status === "pending" && (
                        <Loader2 className={`h-5 w-5 ${COLORS.text.muted}`} />
                      )}
                      {doc.status === "failed" && (
                        <AlertCircle
                          className={`h-5 w-5 ${COLORS.status.error}`}
                        />
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() =>
                        setSummaryModal({
                          isOpen: true,
                          documentId: doc.id,
                          documentName: doc.name,
                        })
                      }
                      disabled={doc.status !== "completed"}
                      title="Generate summary"
                    >
                      <FileSpreadsheet className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => onDocumentSelect?.(doc.id)}
                      disabled={doc.status !== "completed"}
                      title="Chat with document"
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </CardContent>

      {/* Summary Modal */}
      <SummaryModal
        isOpen={summaryModal.isOpen}
        onClose={() => setSummaryModal((prev) => ({ ...prev, isOpen: false }))}
        documentId={summaryModal.documentId}
        documentName={summaryModal.documentName}
      />
    </Card>
  );
}
