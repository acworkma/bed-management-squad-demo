import { Users } from "lucide-react";

export function PatientQueue() {
  return (
    <div className="flex flex-col items-center justify-center py-8 px-4 text-center">
      <div className="rounded-full bg-tower-accent/10 p-3 mb-3">
        <Users className="h-5 w-5 text-tower-accent/60" />
      </div>
      <p className="text-sm text-gray-400">No patients in queue</p>
      <p className="text-xs text-gray-600 mt-1">
        Start a scenario to see incoming patients
      </p>
    </div>
  );
}
