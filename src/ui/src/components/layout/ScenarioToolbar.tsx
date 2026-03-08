import { useState, useCallback } from "react";
import { Play, RotateCcw, Radio } from "lucide-react";
import { cn } from "@/lib/utils";

interface ScenarioToolbarProps {
  eventsConnected: boolean;
  messagesConnected: boolean;
  onReset?: () => void;
}

interface ScenarioStatus {
  name: string;
  running: boolean;
}

export function ScenarioToolbar({ eventsConnected, messagesConnected, onReset }: ScenarioToolbarProps) {
  const [scenario, setScenario] = useState<ScenarioStatus | null>(null);
  const [triggering, setTriggering] = useState(false);

  const connected = eventsConnected || messagesConnected;

  const triggerScenario = useCallback(async (endpoint: string, name: string) => {
    setTriggering(true);
    setScenario({ name, running: true });
    try {
      const res = await fetch(endpoint, { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      // 202 means scenario started — auto-clear after 30s
      setTimeout(() => setScenario(null), 30_000);
    } catch {
      setScenario({ name, running: false });
      setTimeout(() => setScenario(null), 5_000);
    } finally {
      setTriggering(false);
    }
  }, []);

  const handleReset = useCallback(async () => {
    setTriggering(true);
    setScenario(null);
    try {
      const res = await fetch("/api/scenario/seed", { method: "POST" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      onReset?.();
    } catch {
      // silent — state poll will reflect reality
    } finally {
      setTriggering(false);
    }
  }, [onReset]);

  return (
    <div className="flex items-center gap-3 px-4 py-2 bg-tower-surface border-b border-tower-border rounded-t-lg">
      {/* ── Scenario Trigger Buttons ── */}
      <div className="flex items-center gap-2">
        <button
          onClick={() => triggerScenario("/api/scenario/happy-path", "Happy Path")}
          disabled={triggering}
          className={cn(
            "inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors",
            "border border-tower-border bg-tower-bg text-gray-300",
            "hover:border-tower-accent/50 hover:text-tower-accent",
            "disabled:opacity-40 disabled:cursor-not-allowed"
          )}
        >
          <Play className="h-3 w-3" />
          Happy Path
        </button>

        <button
          onClick={() => triggerScenario("/api/scenario/disruption-replan", "Disruption + Replan")}
          disabled={triggering}
          className={cn(
            "inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors",
            "border border-tower-border bg-tower-bg text-gray-300",
            "hover:border-tower-warning/50 hover:text-tower-warning",
            "disabled:opacity-40 disabled:cursor-not-allowed"
          )}
        >
          <Play className="h-3 w-3" />
          Disruption + Replan
        </button>

        <button
          onClick={handleReset}
          disabled={triggering}
          className={cn(
            "inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors",
            "border border-tower-border bg-tower-bg text-gray-300",
            "hover:border-gray-500 hover:text-gray-100",
            "disabled:opacity-40 disabled:cursor-not-allowed"
          )}
        >
          <RotateCcw className="h-3 w-3" />
          Reset
        </button>
      </div>

      {/* ── Scenario Status ── */}
      {scenario && (
        <div className="flex items-center gap-2 ml-2 text-xs text-gray-400">
          <span className="text-gray-500">Scenario:</span>
          <span className="text-gray-200 font-medium">{scenario.name}</span>
          <span className="text-gray-500">—</span>
          {scenario.running ? (
            <span className="inline-flex items-center gap-1 text-tower-accent">
              <span className="relative flex h-1.5 w-1.5">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-tower-accent opacity-75" />
                <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-tower-accent" />
              </span>
              Running
            </span>
          ) : (
            <span className="text-tower-error">Failed</span>
          )}
        </div>
      )}

      {/* ── Spacer ── */}
      <div className="flex-1" />

      {/* ── Connection Status ── */}
      <div className="flex items-center gap-1.5 text-xs">
        <Radio className="h-3 w-3 text-gray-500" />
        <span
          className={cn(
            "inline-flex items-center gap-1.5 font-medium",
            connected ? "text-tower-success" : "text-tower-error"
          )}
        >
          <span
            className={cn(
              "h-1.5 w-1.5 rounded-full",
              connected ? "bg-tower-success" : "bg-tower-error"
            )}
          />
          {connected ? "Connected" : "Disconnected"}
        </span>
      </div>
    </div>
  );
}
