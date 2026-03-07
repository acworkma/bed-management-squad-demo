import { Activity } from "lucide-react";

export function EventTimeline() {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 text-center">
      <div className="rounded-full bg-tower-accent/10 p-4 mb-4">
        <Activity className="h-6 w-6 text-tower-accent/60" />
      </div>
      <p className="text-sm text-gray-400">No events yet</p>
      <p className="text-xs text-gray-600 mt-1.5 max-w-[240px]">
        System events will appear chronologically as scenarios execute
      </p>
    </div>
  );
}
