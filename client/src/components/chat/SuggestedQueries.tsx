"use client";

import { Button } from "@/components/ui/button";
import { Sparkles } from "lucide-react";

type SuggestedQueriesProps = {
  queries: string[];
  onQueryClick: (query: string) => void;
  disabled?: boolean;
};

export const SuggestedQueries = ({
  queries,
  onQueryClick,
  disabled = false,
}: SuggestedQueriesProps) => {
  if (!queries || queries.length === 0) return null;

  return (
    <div className="flex flex-col gap-2 sm:gap-3 py-2 sm:py-3">
      <div className="flex items-center gap-1.5 sm:gap-2 text-xs sm:text-sm text-muted-foreground">
        <Sparkles className="h-3 w-3 sm:h-3.5 sm:w-3.5" />
        <span>You might also be interested in:</span>
      </div>
      <div className="flex flex-wrap gap-1.5 sm:gap-2">
        {queries.map((query, index) => (
          <Button
            key={index}
            variant="outline"
            size="sm"
            onClick={() => onQueryClick(query)}
            disabled={disabled}
            className="text-xs sm:text-sm h-auto py-1.5 sm:py-2 px-2.5 sm:px-3 hover:bg-primary hover:text-primary-foreground transition-colors"
            tabIndex={0}
            aria-label={`Suggested query: ${query}`}
          >
            {query}
          </Button>
        ))}
      </div>
    </div>
  );
};
