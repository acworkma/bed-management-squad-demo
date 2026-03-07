import { MessageSquare, Link } from "lucide-react";
import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";
import { intentTagBadge, agentColor } from "@/lib/colors";
import type { AgentMessage } from "@/types/api";

interface AgentConversationProps {
  messages: AgentMessage[];
}

function relativeTime(ts: string): string {
  const diff = Date.now() - new Date(ts).getTime();
  const secs = Math.floor(diff / 1000);
  if (secs < 60) return `${secs}s ago`;
  const mins = Math.floor(secs / 60);
  if (mins < 60) return `${mins}m ago`;
  return `${Math.floor(mins / 60)}h ago`;
}

export function AgentConversation({ messages }: AgentConversationProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 flex-col items-center justify-center px-4 text-center">
        <div className="rounded-full bg-tower-accent/10 p-4 mb-4">
          <MessageSquare className="h-6 w-6 text-tower-accent/60" />
        </div>
        <p className="text-sm text-gray-400">Waiting for scenario to start…</p>
        <p className="text-xs text-gray-600 mt-1.5 max-w-[240px]">
          Agent messages and tool calls will stream here in real time
        </p>
        <div className="mt-6 flex items-center gap-1.5">
          <span className="h-1.5 w-1.5 rounded-full bg-tower-accent/40 animate-pulse" />
          <span className="h-1.5 w-1.5 rounded-full bg-tower-accent/40 animate-pulse [animation-delay:300ms]" />
          <span className="h-1.5 w-1.5 rounded-full bg-tower-accent/40 animate-pulse [animation-delay:600ms]" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-1 flex-col w-full p-3 space-y-3">
      {messages.map((msg) => {
        const colors = agentColor(msg.agent_name);
        return (
          <div key={msg.id} className="flex gap-2.5 group">
            {/* Avatar */}
            <div
              className={cn(
                "h-7 w-7 rounded-full ring-1 flex items-center justify-center text-[10px] font-bold shrink-0 mt-0.5",
                colors.ring,
                colors.bg,
                colors.text
              )}
            >
              {msg.agent_name.charAt(0).toUpperCase()}
            </div>

            <div className="flex-1 min-w-0">
              {/* Header */}
              <div className="flex items-center gap-2 flex-wrap">
                <span className={cn("text-xs font-semibold", colors.text)}>
                  {msg.agent_name}
                </span>
                <span className="text-[10px] text-gray-600">{msg.agent_role}</span>
                <span
                  className={cn(
                    "inline-flex items-center rounded px-1.5 py-0.5 text-[9px] font-bold uppercase",
                    intentTagBadge(msg.intent_tag)
                  )}
                >
                  {msg.intent_tag}
                </span>
                <span className="text-[10px] text-gray-600 font-mono ml-auto shrink-0">
                  {relativeTime(msg.timestamp)}
                </span>
              </div>

              {/* Content */}
              <p className="text-xs text-gray-300 mt-1 leading-relaxed whitespace-pre-wrap">
                {msg.content}
              </p>

              {/* Related events */}
              {msg.related_event_ids.length > 0 && (
                <div className="flex items-center gap-1.5 mt-1.5 flex-wrap">
                  <Link className="h-3 w-3 text-gray-600" />
                  {msg.related_event_ids.map((eid) => (
                    <span
                      key={eid}
                      className="inline-flex items-center rounded bg-tower-border px-1.5 py-0.5 text-[9px] font-mono text-gray-400 hover:text-gray-200 transition-colors cursor-default"
                      title={`Event: ${eid}`}
                    >
                      {eid.slice(0, 8)}
                    </span>
                  ))}
                </div>
              )}
            </div>
          </div>
        );
      })}
      <div ref={bottomRef} />
    </div>
  );
}
