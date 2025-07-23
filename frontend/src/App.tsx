import { useState } from "react";
import {
  Brain,
  Upload,
  MessageSquare,
  FileText,
  Sparkles,
  Zap,
  Shield,
  ArrowRight,
} from "lucide-react";
import { FileUpload } from "./components/FileUpload";
import { DocumentList } from "./components/DocumentList";
import { ChatInterface } from "./components/ChatInterface";
import { Card, CardContent } from "./components/ui/card";
import { Button } from "./components/ui/button";
import { APP_CONFIG, UI_MESSAGES, UPLOAD_CONFIG } from "./lib/constants";
import { COLORS, TYPOGRAPHY, LAYOUT } from "./lib/design-system";
type ViewMode = "upload" | "documents" | "chat";

function App() {
  const [viewMode, setViewMode] = useState<ViewMode>("upload");
  const [selectedDocumentId, setSelectedDocumentId] = useState<string>();

  const handleUploadSuccess = () => {
    setViewMode("documents");
  };

  const handleDocumentSelect = (documentId: string) => {
    setSelectedDocumentId(documentId);
    setViewMode("chat");
  };

  const renderContent = () => {
    switch (viewMode) {
      case "upload":
        return (
          <div className={LAYOUT.container.lg}>
            {/* Hero Section */}
            <div className="text-center mb-24">
              <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-blue-500 to-purple-600 rounded-3xl mb-8 shadow-xl">
                <Sparkles className="h-10 w-10 text-white" />
              </div>

              <h1
                className={`text-5xl md:text-6xl font-bold ${COLORS.text.primary} mb-4 bg-gradient-to-r from-gray-900 via-blue-900 to-gray-900 bg-clip-text text-transparent leading-relaxed pb-2`}
              >
                {APP_CONFIG.name}
              </h1>

              <p
                className={`text-xl md:text-2xl ${COLORS.text.secondary} mb-12 max-w-3xl mx-auto ${TYPOGRAPHY.body.large} px-6`}
              >
                {APP_CONFIG.description}
              </p>

              {/* Feature Grid */}
              <div className="grid md:grid-cols-3 gap-8 mb-20">
                <Card className="border-0 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 bg-gradient-to-br from-blue-50 to-blue-100">
                  <CardContent className="text-center py-10">
                    <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-blue-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                      <Zap className="h-8 w-8 text-white" />
                    </div>
                    <h3
                      className={`${TYPOGRAPHY.heading.h4} ${COLORS.text.primary} mb-4`}
                    >
                      Blazing Fast
                    </h3>
                    <p
                      className={`${COLORS.text.secondary} ${TYPOGRAPHY.body.default}`}
                    >
                      Upload any PDF and start chatting in{" "}
                      {UPLOAD_CONFIG.processingTime}. We instantly read
                      everything—text, tables, charts—so you don't have to.
                    </p>
                  </CardContent>
                </Card>

                <Card className="border-0 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 bg-gradient-to-br from-green-50 to-emerald-100">
                  <CardContent className="text-center py-10">
                    <div className="w-16 h-16 bg-gradient-to-br from-green-500 to-green-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                      <Sparkles className="h-8 w-8 text-white" />
                    </div>
                    <h3
                      className={`${TYPOGRAPHY.heading.h4} ${COLORS.text.primary} mb-4`}
                    >
                      Smart Answers
                    </h3>
                    <p
                      className={`${COLORS.text.secondary} ${TYPOGRAPHY.body.default}`}
                    >
                      Ask questions in plain English and get clear answers with
                      exact page numbers. Like having a research assistant who
                      actually read everything.
                    </p>
                  </CardContent>
                </Card>

                <Card className="border-0 shadow-lg hover:shadow-xl transition-all duration-300 hover:-translate-y-1 bg-gradient-to-br from-purple-50 to-purple-100">
                  <CardContent className="text-center py-10">
                    <div className="w-16 h-16 bg-gradient-to-br from-purple-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-6 shadow-lg">
                      <Shield className="h-8 w-8 text-white" />
                    </div>
                    <h3
                      className={`${TYPOGRAPHY.heading.h4} ${COLORS.text.primary} mb-4`}
                    >
                      Never Lose Your Source
                    </h3>
                    <p
                      className={`${COLORS.text.secondary} ${TYPOGRAPHY.body.default}`}
                    >
                      Every answer shows exactly where it came from—page
                      numbers, quotes, the works. No more "where did I read
                      that?"
                    </p>
                  </CardContent>
                </Card>
              </div>
            </div>

            {/* Upload Component */}
            <div className="mb-20">
              <FileUpload onUploadSuccess={handleUploadSuccess} />
            </div>

            {/* Call to Action */}
            <Card className="bg-gradient-to-r from-blue-600 to-purple-600 border-0 text-white shadow-2xl">
              <CardContent className="p-12 text-center">
                <h3 className="text-3xl font-bold mb-6">Give it a try!</h3>
                <p className="text-blue-100 mb-8 text-xl leading-relaxed">
                  Upload any PDF above and watch the magic happen. Your
                  documents have never been this easy to navigate.
                </p>
                <div className="flex items-center justify-center space-x-8 text-lg">
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                    <span>100% Private</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                    <span>Up to {UPLOAD_CONFIG.maxFileSize}</span>
                  </div>
                  <div className="flex items-center space-x-3">
                    <div className="w-3 h-3 bg-green-400 rounded-full animate-pulse"></div>
                    <span>Works in {UPLOAD_CONFIG.processingTime}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        );

      case "documents":
        return (
          <div className={LAYOUT.container.xl}>
            <div className="mb-12">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between mb-12 gap-6">
                <div>
                  <h1
                    className={`text-4xl lg:text-5xl font-bold ${COLORS.text.primary} mb-4 bg-gradient-to-r from-gray-900 to-blue-900 bg-clip-text text-transparent leading-relaxed pb-1`}
                  >
                    {UI_MESSAGES.documents.title}
                  </h1>
                  <p
                    className={`text-lg lg:text-xl ${COLORS.text.secondary} ${TYPOGRAPHY.body.large}`}
                  >
                    {UI_MESSAGES.documents.subtitle}
                  </p>
                </div>

                <Button
                  variant="primary"
                  onClick={() => setViewMode("upload")}
                  size="lg"
                  className="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 shadow-lg hover:shadow-xl transition-all"
                >
                  <Sparkles className="h-5 w-5 mr-2" />
                  Add More PDFs
                </Button>
              </div>
            </div>

            <DocumentList onDocumentSelect={handleDocumentSelect} />

            {/* Next Steps Card */}
            <Card className="mt-16 bg-gradient-to-r from-green-50 to-emerald-100 border-green-200 shadow-xl">
              <CardContent className="p-12">
                <div className="flex items-start space-x-8">
                  <div className="flex-shrink-0 w-16 h-16 bg-green-500 rounded-full flex items-center justify-center text-white font-bold text-2xl shadow-xl">
                    ✓
                  </div>
                  <div className="flex-1">
                    <h3 className="text-3xl font-bold text-green-900 mb-4">
                      Ready to Chat!
                    </h3>
                    <p className="text-green-800 text-xl mb-8 leading-relaxed">
                      Your documents are processed and ready for intelligent
                      conversations. Click on any document above to start asking
                      questions, or chat with all documents simultaneously for
                      comprehensive insights.
                    </p>
                    <Button
                      onClick={() => setViewMode("chat")}
                      className="bg-green-600 hover:bg-green-700 text-white px-10 py-4 text-xl shadow-xl hover:shadow-2xl transition-all"
                    >
                      Start Multi-Document Chat
                      <ArrowRight className="h-6 w-6 ml-3" />
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>
        );

      case "chat":
        return (
          <div className="h-screen flex flex-col">
            {/* Modern header - more minimal */}
            <div className="flex-shrink-0 bg-white border-b border-gray-100 px-6 py-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <Button
                    variant="ghost"
                    onClick={() => setViewMode("documents")}
                    className="text-gray-600 hover:text-gray-900"
                  >
                    ← Back to Library
                  </Button>
                  <div className="h-6 w-px bg-gray-300" />
                  <div>
                    <h1 className="text-lg font-semibold text-gray-900">
                      {selectedDocumentId
                        ? "Document Chat"
                        : "Multi-Document Chat"}
                    </h1>
                    <p className="text-sm text-gray-500">
                      {selectedDocumentId
                        ? "Chatting with selected document"
                        : "Searching across all documents"}
                    </p>
                  </div>
                </div>

                <div className="flex items-center space-x-3">
                  {selectedDocumentId && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => setSelectedDocumentId(undefined)}
                    >
                      Switch to All Docs
                    </Button>
                  )}
                </div>
              </div>
            </div>

            {/* Chat interface takes full remaining space */}
            <div className="flex-1 min-h-0">
              <ChatInterface
                documentId={selectedDocumentId}
                className="h-full"
              />
            </div>
          </div>
        );
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 via-blue-50 to-gray-100">
      {/* Navigation */}
      <nav className="bg-white/95 backdrop-blur-xl border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className={`${LAYOUT.container.xl} px-6`}>
          <div className="flex justify-between items-center h-20">
            <div className="flex items-center space-x-4">
              <div className="p-2.5 bg-gradient-to-br from-blue-500 to-purple-600 rounded-xl shadow-lg">
                <Brain className="h-8 w-8 text-white" />
              </div>
              <div>
                <span
                  className={`text-xl font-bold ${COLORS.text.primary} leading-relaxed py-1`}
                >
                  AskMyDocs
                </span>
                <div className={`${TYPOGRAPHY.body.xs} ${COLORS.text.muted}`}>
                  Your documents, answered
                </div>
              </div>
            </div>

            <div className="flex items-center space-x-2">
              <Button
                variant={viewMode === "upload" ? "primary" : "ghost"}
                size="default"
                onClick={() => setViewMode("upload")}
                className="font-medium"
              >
                <Upload className="h-4 w-4 mr-2" />
                Upload
              </Button>

              <Button
                variant={viewMode === "documents" ? "primary" : "ghost"}
                size="default"
                onClick={() => setViewMode("documents")}
                className="font-medium"
              >
                <FileText className="h-4 w-4 mr-2" />
                Documents
              </Button>

              <Button
                variant={viewMode === "chat" ? "primary" : "ghost"}
                size="default"
                onClick={() => setViewMode("chat")}
                className="font-medium"
              >
                <MessageSquare className="h-4 w-4 mr-2" />
                Chat
              </Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className={LAYOUT.section.large}>{renderContent()}</main>
    </div>
  );
}

export default App;
