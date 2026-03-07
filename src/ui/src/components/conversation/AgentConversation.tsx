import { MessageSquare } from "lucide-react";

export function AgentConversation() {
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
