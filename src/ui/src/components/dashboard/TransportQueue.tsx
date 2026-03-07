import { Truck } from "lucide-react";

export function TransportQueue() {
  return (
    <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
      <div className="rounded-full bg-tower-accent/10 p-3 mb-3">
        <Truck className="h-5 w-5 text-tower-accent/60" />
      </div>
      <p className="text-sm text-gray-400">No active transports</p>
      <p className="text-xs text-gray-600 mt-1">
        Transport requests will queue here
      </p>
    </div>
  );
}
