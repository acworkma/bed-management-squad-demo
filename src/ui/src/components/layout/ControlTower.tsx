import { Users, BedDouble, Truck, MessageSquare, Activity } from "lucide-react";
import { PaneHeader } from "@/components/layout/PaneHeader";
import { PatientQueue } from "@/components/dashboard/PatientQueue";
import { BedBoard } from "@/components/dashboard/BedBoard";
import { TransportQueue } from "@/components/dashboard/TransportQueue";
import { AgentConversation } from "@/components/conversation/AgentConversation";
import { EventTimeline } from "@/components/timeline/EventTimeline";

export function ControlTower() {
  return (
    <div className="h-screen w-screen overflow-hidden grid grid-cols-[55fr_45fr] grid-rows-[1fr] gap-2 p-2">
      {/* ── Left Pane: Ops Dashboard ── */}
      <div className="flex flex-col gap-2 overflow-hidden">
        {/* Patient Queue */}
        <section className="flex flex-col rounded-lg border border-tower-border bg-tower-surface overflow-hidden">
          <PaneHeader icon={Users} title="Patient Queue" />
          <div className="overflow-y-auto flex-1">
            <PatientQueue />
          </div>
        </section>

        {/* Bed Board — takes the most space */}
        <section className="flex flex-col flex-[2] rounded-lg border border-tower-border bg-tower-surface overflow-hidden">
          <PaneHeader icon={BedDouble} title="Bed Board" />
          <div className="overflow-y-auto flex-1">
            <BedBoard />
          </div>
        </section>

        {/* Transport Queue */}
        <section className="flex flex-col rounded-lg border border-tower-border bg-tower-surface overflow-hidden">
          <PaneHeader icon={Truck} title="Transport Queue" />
          <div className="overflow-y-auto flex-1">
            <TransportQueue />
          </div>
        </section>
      </div>

      {/* ── Right Column: split top/bottom ── */}
      <div className="flex flex-col gap-2 overflow-hidden">
        {/* Agent Conversation — 55% of right column */}
        <section className="flex flex-col flex-[55] rounded-lg border border-tower-border bg-tower-surface overflow-hidden">
          <PaneHeader icon={MessageSquare} title="Agent Conversation" />
          <div className="overflow-y-auto flex-1 flex">
            <AgentConversation />
          </div>
        </section>

        {/* Event Timeline — 45% of right column */}
        <section className="flex flex-col flex-[45] rounded-lg border border-tower-border bg-tower-surface overflow-hidden">
          <PaneHeader icon={Activity} title="Event Timeline" />
          <div className="overflow-y-auto flex-1 flex">
            <EventTimeline />
          </div>
        </section>
      </div>
    </div>
  );
}
