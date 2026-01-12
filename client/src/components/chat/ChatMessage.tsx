"use client";

import { cn } from "@/lib/utils";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Bot, User } from "lucide-react";
import type { Message } from "./types";

type ChatMessageProps = {
  message: Message;
};

export const ChatMessage = ({ message }: ChatMessageProps) => {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-2 sm:gap-3 p-3 sm:p-4",
        isUser ? "flex-row-reverse" : "flex-row"
      )}
    >
      <Avatar className="h-8 w-8 sm:h-10 sm:w-10 shrink-0">
        <AvatarFallback
          className={cn(
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-secondary text-secondary-foreground"
          )}
        >
          {isUser ? (
            <User className="h-4 w-4 sm:h-5 sm:w-5" />
          ) : (
            <Bot className="h-4 w-4 sm:h-5 sm:w-5" />
          )}
        </AvatarFallback>
      </Avatar>
      <div
        className={cn(
          "flex flex-col max-w-[75%] sm:max-w-[70%]",
          isUser ? "items-end" : "items-start"
        )}
      >
        <div
          className={cn(
            "rounded-2xl px-3 py-2 sm:px-4 sm:py-2.5 text-sm sm:text-base",
            isUser
              ? "bg-primary text-primary-foreground rounded-br-md"
              : "bg-muted text-foreground rounded-bl-md"
          )}
        >
          <p className="whitespace-pre-wrap break-words">{message.content}</p>
        </div>
        <span
          className="text-[10px] sm:text-xs text-muted-foreground mt-1 px-1"
          suppressHydrationWarning
        >
          {message.timestamp.toLocaleTimeString([], {
            hour: "2-digit",
            minute: "2-digit",
          })}
        </span>
      </div>
    </div>
  );
};
