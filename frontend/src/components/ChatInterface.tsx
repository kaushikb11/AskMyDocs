import { useState, useRef, useEffect } from "react";
import {
  Bot,
  FileText,
  Sparkles,
  ArrowUp,
  Plus,
  BookOpen,
  Zap,
  Search,
  TrendingUp,
} from "lucide-react";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";

import {
  askQuestion,
  APIError,
  type ChatRequest,
  type ChatResponse,
  type SourceReference,
} from "../lib/api";
import {
  sortSourcesByRelevance,
  hasHighQualitySources,
} from "../lib/source-utils";

interface ChatInterfaceProps {
  documentId?: string;
  conversationId?: string;
  onNewConversation?: (conversationId: string) => void;
  className?: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: SourceReference[];
  timestamp?: string;
}

// Conversation starter suggestions
const CONVERSATION_STARTERS = [
  {
    icon: Search,
    text: "What are the key findings in this document?",
    category: "Summary",
  },
  {
    icon: TrendingUp,
    text: "What are the main conclusions?",
    category: "Analysis",
  },
  {
    icon: BookOpen,
    text: "Explain the methodology used",
    category: "Deep Dive",
  },
  {
    icon: Zap,
    text: "What should I know before reading this?",
    category: "Quick Start",
  },
];

// Utility function to generate session ID
function generateSessionId() {
  return (
    "session-" +
    Date.now().toString(36) +
    "-" +
    Math.random().toString(36).substr(2, 9)
  );
}

function TypingAnimation() {
  return (
    <div className="flex space-x-1 items-center">
      <div className="flex space-x-1">
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
        <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
      </div>
      <span className="text-sm text-gray-500 ml-2">Thinking...</span>
    </div>
  );
}

function Source({
  source,
  isCompact = false,
}: {
  source: SourceReference;
  isCompact?: boolean;
}) {
  if (isCompact) {
    return (
      <div className="inline-flex items-center space-x-2 bg-gray-50 px-3 py-1.5 rounded-full text-xs">
        <FileText className="h-3 w-3 text-gray-600" />
        <span className="text-gray-700">{source.source_document}</span>
        <span className="text-gray-500">p.{source.page_number + 1}</span>
      </div>
    );
  }

  return (
    <div className="bg-white border border-gray-200 rounded-lg p-4 hover:shadow-sm transition-all">
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center space-x-2">
          <FileText className="h-4 w-4 text-gray-600" />
          <span className="font-medium text-sm text-gray-900">
            {source.source_document}
          </span>
          <span className="text-xs text-gray-500">
            Page {source.page_number + 1}
          </span>
        </div>
        {source.quality_score && source.quality_score > 0.8 && (
          <Badge variant="success" className="text-xs">
            High quality
          </Badge>
        )}
      </div>
      <p className="text-sm text-gray-700 leading-relaxed">
        {source.content_preview}
      </p>
    </div>
  );
}

function EmptyState({
  onStarterClick,
}: {
  onStarterClick: (text: string) => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center p-8">
      <div className="w-16 h-16 bg-gradient-to-br from-blue-500 to-purple-600 rounded-2xl flex items-center justify-center mb-6 shadow-lg">
        <Sparkles className="h-8 w-8 text-white" />
      </div>

      <h3 className="text-xl font-semibold text-gray-900 mb-2">
        What would you like to know?
      </h3>
      <p className="text-gray-600 text-base mb-8 max-w-md">
        Ask anything about your documents. I'll find the relevant information
        and provide detailed answers with sources.
      </p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full max-w-2xl">
        {CONVERSATION_STARTERS.map((starter, idx) => (
          <button
            key={idx}
            onClick={() => onStarterClick(starter.text)}
            className="flex items-center space-x-3 p-4 text-left bg-gray-50 hover:bg-gray-100 rounded-xl transition-colors group"
          >
            <div className="flex-shrink-0 w-8 h-8 bg-white rounded-lg flex items-center justify-center group-hover:bg-blue-50 transition-colors">
              <starter.icon className="h-4 w-4 text-gray-600 group-hover:text-blue-600" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-medium text-gray-900 mb-1">
                {starter.text}
              </p>
              <p className="text-xs text-gray-500">{starter.category}</p>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export function ChatInterface({ documentId, className }: ChatInterfaceProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Session management
  const [sessionId, setSessionId] = useState<string>(() => {
    // Get existing session or create new one
    const stored = localStorage.getItem("chat-session-id");
    return stored || generateSessionId();
  });

  // Persist session ID and messages
  useEffect(() => {
    localStorage.setItem("chat-session-id", sessionId);
  }, [sessionId]);

  useEffect(() => {
    // Load messages for current session
    const savedMessages = localStorage.getItem(`chat-messages-${sessionId}`);
    if (savedMessages) {
      try {
        setMessages(JSON.parse(savedMessages));
      } catch (error) {
        console.error("Failed to load saved messages:", error);
      }
    }
  }, [sessionId]);

  useEffect(() => {
    // Save messages for current session
    if (messages.length > 0) {
      localStorage.setItem(
        `chat-messages-${sessionId}`,
        JSON.stringify(messages),
      );
    }
  }, [messages, sessionId]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleNewSession = () => {
    const newSessionId = generateSessionId();
    setSessionId(newSessionId);
    setMessages([]);

    localStorage.removeItem(`chat-messages-${newSessionId}`);
  };

  const handleSend = async (question?: string) => {
    const finalQuestion = question || input.trim();
    if (!finalQuestion) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: finalQuestion,
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);

    try {
      const chatRequest: ChatRequest = {
        question: finalQuestion,
        document_id: documentId,
        session_id: sessionId, // Include session ID
        include_sources: true,
        max_sources: 3,
      };

      const response: ChatResponse = await askQuestion(chatRequest);

      const aiMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: response.answer,
        sources: response.sources
          ? sortSourcesByRelevance(response.sources)
          : undefined,
        timestamp: response.timestamp,
      };

      setMessages((prev) => [...prev, aiMessage]);
    } catch (error) {
      console.error("Chat API error:", error);

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content:
          error instanceof APIError
            ? `I encountered an error: ${error.message}`
            : "Something went wrong. Please try again.",
        timestamp: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const autoResize = () => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height =
        Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  };

  return (
    <div className={`flex flex-col h-full bg-white ${className}`}>
      {/* Header - Enhanced with session info */}
      <div className="flex items-center justify-between p-4 border-b border-gray-100">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
            <Bot className="h-4 w-4 text-white" />
          </div>
          <div>
            <h2 className="font-medium text-gray-900">
              {documentId ? "Document Assistant" : "Multi-Document Assistant"}
            </h2>
            <p className="text-xs text-gray-500">
              Session: {sessionId.slice(8, 16)}... • {messages.length} messages
            </p>
          </div>
        </div>

        <Button variant="ghost" size="sm" onClick={handleNewSession}>
          <Plus className="h-4 w-4 mr-1" />
          New Session
        </Button>
      </div>

      {/* Messages Area - Dynamic height */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <EmptyState onStarterClick={handleSend} />
        ) : (
          <div className="max-w-4xl mx-auto p-4 space-y-6">
            {messages.map((message) => (
              <div key={message.id} className="group">
                {message.role === "user" ? (
                  // User message - Clean and minimal
                  <div className="flex justify-end">
                    <div className="bg-gray-900 text-white rounded-2xl rounded-br-sm px-4 py-3 max-w-3xl">
                      <p className="text-sm leading-relaxed">
                        {message.content}
                      </p>
                    </div>
                  </div>
                ) : (
                  // Assistant message - More spacious and detailed
                  <div className="flex space-x-4">
                    <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                      <Bot className="h-4 w-4 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="prose prose-sm max-w-none">
                        <p className="text-gray-900 leading-relaxed whitespace-pre-wrap mb-4">
                          {message.content}
                        </p>
                      </div>

                      {/* Inline sources - More integrated */}
                      {message.sources && message.sources.length > 0 && (
                        <div className="space-y-3">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-medium text-gray-600">
                              Sources
                            </span>
                            <div className="flex items-center space-x-2">
                              <Badge variant="outline" className="text-xs">
                                {message.sources.length} reference
                                {message.sources.length > 1 ? "s" : ""}
                              </Badge>
                              {hasHighQualitySources(message.sources) && (
                                <Badge variant="success" className="text-xs">
                                  ✨ High quality
                                </Badge>
                              )}
                            </div>
                          </div>

                          <div className="grid gap-2">
                            {message.sources.map((source) => (
                              <Source key={source.chunk_id} source={source} />
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            ))}

            {loading && (
              <div className="flex space-x-4">
                <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg flex items-center justify-center">
                  <Bot className="h-4 w-4 text-white" />
                </div>
                <div className="flex-1">
                  <TypingAnimation />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area - Modern and inviting */}
      <div className="border-t border-gray-100 p-4">
        <div className="max-w-4xl mx-auto">
          <div className="relative flex items-end space-x-3 bg-gray-50 rounded-2xl p-3">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                autoResize();
              }}
              onKeyPress={handleKeyPress}
              placeholder={
                documentId
                  ? "Ask about this document..."
                  : "Ask anything about your documents..."
              }
              className="flex-1 bg-transparent resize-none outline-none text-sm leading-relaxed min-h-[24px] max-h-[120px] placeholder-gray-500"
              disabled={loading}
              rows={1}
            />
            <Button
              onClick={() => handleSend()}
              disabled={!input.trim() || loading}
              size="sm"
              className="rounded-xl bg-gray-900 hover:bg-gray-800 text-white p-2 transition-all disabled:opacity-50"
            >
              <ArrowUp className="h-4 w-4" />
            </Button>
          </div>

          {messages.length === 0 && (
            <p className="text-xs text-gray-500 text-center mt-2">
              Press Enter to send • Shift + Enter for new line • Session memory
              active
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
