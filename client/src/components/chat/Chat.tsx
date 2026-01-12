"use client";

import { useState, useRef, useEffect, type KeyboardEvent } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Send, Loader2, RotateCcw, CheckCircle2, Check, X, RefreshCw } from "lucide-react";
import { ChatMessage } from "./ChatMessage";
import type { Message } from "./types";

const generateId = () => Math.random().toString(36).substring(2, 9);

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const INITIAL_MESSAGE: Message = {
  id: generateId(),
  role: "assistant",
  content:
    "Hello! I'm your ASU enrollment data assistant. I can help you query student enrollment information. Just tell me what you'd like to know - for example, 'How many students were enrolled in Fall 2024?' or 'Show me graduate enrollment trends.'",
  timestamp: new Date(),
};

export const Chat = () => {
  const [messages, setMessages] = useState<Message[]>([INITIAL_MESSAGE]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isConfirmed, setIsConfirmed] = useState(false);
  const [isAwaitingConfirmation, setIsAwaitingConfirmation] = useState(false);
  const scrollAreaRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    if (scrollAreaRef.current) {
      const scrollContainer = scrollAreaRef.current.querySelector(
        "[data-radix-scroll-area-viewport]"
      );
      if (scrollContainer) {
        scrollContainer.scrollTop = scrollContainer.scrollHeight;
      }
    }
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleStartNewConversation = () => {
    setMessages([
      {
        ...INITIAL_MESSAGE,
        id: generateId(),
        timestamp: new Date(),
      },
    ]);
    setConversationId(null);
    setIsConfirmed(false);
    setIsAwaitingConfirmation(false);
    setInput("");
    console.log("Started new conversation");
  };

  const handleSendMessage = async () => {
    const trimmedInput = input.trim();
    if (!trimmedInput || isLoading) return;

    const userMessage: Message = {
      id: generateId(),
      role: "user",
      content: trimmedInput,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    console.log("Sending message:", trimmedInput);

    try {
      const response = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: trimmedInput,
          conversation_id: conversationId,
        }),
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      console.log("Response received:", data);

      if (data.conversation_id) {
        setConversationId(data.conversation_id);
      }

      if (data.confirmed) {
        setIsConfirmed(true);
        setIsAwaitingConfirmation(false);
        console.log("Query confirmed!");
      } else if (data.awaiting_confirmation) {
        setIsAwaitingConfirmation(true);
        console.log("Awaiting confirmation");
      } else {
        setIsAwaitingConfirmation(false);
      }

      const assistantMessage: Message = {
        id: generateId(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error sending message:", error);

      const errorMessage: Message = {
        id: generateId(),
        role: "assistant",
        content:
          "Sorry, I encountered an error connecting to the server. Please make sure the backend is running on http://localhost:8000",
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  const handleConfirmationResponse = async (response: "yes" | "no") => {
    if (isLoading) return;

    const userMessage: Message = {
      id: generateId(),
      role: "user",
      content: response === "yes" ? "Yes" : "No, let me change something",
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const apiResponse = await fetch(`${API_URL}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: response === "yes" ? "yes" : "I want to change something",
          conversation_id: conversationId,
        }),
      });

      if (!apiResponse.ok) {
        throw new Error(`HTTP error! status: ${apiResponse.status}`);
      }

      const data = await apiResponse.json();
      console.log("Confirmation response:", data);

      if (data.confirmed) {
        setIsConfirmed(true);
        setIsAwaitingConfirmation(false);
      } else {
        setIsAwaitingConfirmation(data.awaiting_confirmation || false);
      }

      const assistantMessage: Message = {
        id: generateId(),
        role: "assistant",
        content: data.response,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Error sending confirmation:", error);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full w-full max-w-3xl mx-auto bg-background border rounded-lg sm:rounded-xl shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 sm:px-6 sm:py-4 border-b">
        <h1 className="text-base sm:text-lg font-semibold">
          ASU Enrollment Assistant
        </h1>
        <span className="text-xs sm:text-sm text-muted-foreground">
          {messages.length} messages
        </span>
      </div>

      {/* Messages */}
      <ScrollArea ref={scrollAreaRef} className="flex-1 px-2 sm:px-4">
        <div className="py-2 sm:py-4">
          {messages.map((message) => (
            <ChatMessage key={message.id} message={message} />
          ))}
          {isLoading && (
            <div className="flex gap-2 sm:gap-3 p-3 sm:p-4">
              <div className="h-8 w-8 sm:h-10 sm:w-10 rounded-full bg-secondary flex items-center justify-center">
                <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin text-muted-foreground" />
              </div>
              <div className="flex items-center">
                <span className="text-sm text-muted-foreground">
                  Thinking...
                </span>
              </div>
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Footer - Input, Confirmation Buttons, or New Conversation */}
      <div className="p-3 sm:p-4 border-t">
        {isConfirmed ? (
          <div className="flex flex-col items-center gap-3">
            <div className="flex items-center gap-2 text-sm text-green-600 dark:text-green-400">
              <CheckCircle2 className="h-4 w-4" />
              <span>Query complete!</span>
            </div>
            <Button
              onClick={handleStartNewConversation}
              variant="outline"
              className="w-full sm:w-auto"
            >
              <RotateCcw className="h-4 w-4 mr-2" />
              Start New Conversation
            </Button>
          </div>
        ) : isAwaitingConfirmation ? (
          <div className="flex flex-col gap-3">
            <div className="flex gap-2 sm:gap-3 justify-center">
              <Button
                onClick={() => handleConfirmationResponse("yes")}
                disabled={isLoading}
                className="flex-1 sm:flex-none bg-green-600 hover:bg-green-700"
              >
                {isLoading ? (
                  <Loader2 className="h-4 w-4 animate-spin mr-2" />
                ) : (
                  <Check className="h-4 w-4 mr-2" />
                )}
                Yes, Search
              </Button>
              <Button
                onClick={() => handleConfirmationResponse("no")}
                disabled={isLoading}
                variant="outline"
                className="flex-1 sm:flex-none"
              >
                <X className="h-4 w-4 mr-2" />
                Change
              </Button>
              <Button
                onClick={handleStartNewConversation}
                disabled={isLoading}
                variant="ghost"
                className="flex-1 sm:flex-none"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Start Over
              </Button>
            </div>
          </div>
        ) : (
          <div className="flex gap-2 sm:gap-3">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask about enrollment data..."
              disabled={isLoading}
              className="flex-1 text-sm sm:text-base h-10 sm:h-11"
              aria-label="Chat message input"
            />
            <Button
              onClick={handleSendMessage}
              disabled={!input.trim() || isLoading}
              size="icon"
              className="h-10 w-10 sm:h-11 sm:w-11 shrink-0"
              aria-label="Send message"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 sm:h-5 sm:w-5 animate-spin" />
              ) : (
                <Send className="h-4 w-4 sm:h-5 sm:w-5" />
              )}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};
