"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";

interface Schedule {
  schedule_id: string;
  name: string;
  cron: string;
  task_type: string;
  payload: Record<string, unknown>;
  enabled: boolean;
  last_run: string | null;
  last_status: string | null;
  run_count: number;
  consecutive_failures: number;
}

const CRON_PRESETS = [
  { label: "Every 5 minutes", value: "*/5 * * * *" },
  { label: "Every 15 minutes", value: "*/15 * * * *" },
  { label: "Every hour", value: "@hourly" },
  { label: "Daily at midnight", value: "@daily" },
  { label: "Weekly", value: "@weekly" },
  { label: "Monthly", value: "@monthly" },
  { label: "Custom", value: "" },
];

export default function SchedulesPage() {
  const router = useRouter();
  const [schedules, setSchedules] = useState<Schedule[]>([]);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);

  // Form state
  const [name, setName] = useState("");
  const [cronPreset, setCronPreset] = useState("@hourly");
  const [customCron, setCustomCron] = useState("");
  const [taskType, setTaskType] = useState("shell");
  const [command, setCommand] = useState("");
  const [message, setMessage] = useState("");

  useEffect(() => {
    if (!api.isLoggedIn()) {
      router.push("/");
      return;
    }
    loadSchedules();
  }, []);

  async function loadSchedules() {
    try {
      const data = await api.getSchedules();
      setSchedules(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to load schedules");
    }
  }

  async function handleCreate() {
    if (!name.trim()) return;
    setError("");

    const cron = cronPreset || customCron;
    if (!cron) {
      setError("Please select or enter a cron schedule");
      return;
    }

    const payload: Record<string, unknown> = {};
    if (taskType === "shell") payload.command = command;
    if (taskType === "conversation") payload.message = message;

    try {
      await api.createSchedule(name.trim(), cron, taskType, payload);
      setName("");
      setCommand("");
      setMessage("");
      setShowCreate(false);
      loadSchedules();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to create schedule");
    }
  }

  async function toggleEnabled(sched: Schedule) {
    try {
      await api.updateSchedule(sched.schedule_id, { enabled: !sched.enabled });
      loadSchedules();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to update schedule");
    }
  }

  async function handleDelete(scheduleId: string) {
    if (!confirm("Delete this schedule?")) return;
    try {
      await api.deleteSchedule(scheduleId);
      loadSchedules();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "Failed to delete schedule");
    }
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white">
      <div className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-3xl font-bold">Scheduled Tasks</h1>
            <p className="text-zinc-400 text-sm mt-1">
              Automate recurring tasks with cron-like scheduling
            </p>
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => setShowCreate(!showCreate)}
              className="px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-500 text-sm"
            >
              {showCreate ? "Cancel" : "+ New Schedule"}
            </button>
            <button
              onClick={() => router.push("/chat")}
              className="px-4 py-2 bg-zinc-800 rounded-lg hover:bg-zinc-700 text-sm"
            >
              Back to Chat
            </button>
          </div>
        </div>

        {error && (
          <div className="bg-red-900/30 border border-red-800 text-red-300 px-4 py-2 rounded-lg mb-4">
            {error}
          </div>
        )}

        {/* Create Form */}
        {showCreate && (
          <div className="bg-zinc-900 rounded-xl p-5 mb-6 space-y-4">
            <h2 className="text-lg font-semibold">Create New Schedule</h2>

            <div>
              <label className="block text-sm text-zinc-400 mb-1">Name</label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="e.g., Daily System Report"
                className="w-full bg-zinc-800 text-white px-3 py-2 rounded-lg border border-zinc-700 focus:border-blue-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-sm text-zinc-400 mb-1">Schedule</label>
              <div className="flex flex-wrap gap-2 mb-2">
                {CRON_PRESETS.map((p) => (
                  <button
                    key={p.label}
                    onClick={() => setCronPreset(p.value)}
                    className={`px-3 py-1.5 rounded-lg text-xs transition ${
                      cronPreset === p.value
                        ? "bg-blue-600 text-white"
                        : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                    }`}
                  >
                    {p.label}
                  </button>
                ))}
              </div>
              {cronPreset === "" && (
                <input
                  type="text"
                  value={customCron}
                  onChange={(e) => setCustomCron(e.target.value)}
                  placeholder="*/5 * * * * (min hour day month weekday)"
                  className="w-full bg-zinc-800 text-white px-3 py-2 rounded-lg border border-zinc-700 focus:border-blue-500 focus:outline-none font-mono text-sm"
                />
              )}
            </div>

            <div>
              <label className="block text-sm text-zinc-400 mb-1">Task Type</label>
              <div className="flex gap-2">
                {["shell", "conversation", "tool"].map((t) => (
                  <button
                    key={t}
                    onClick={() => setTaskType(t)}
                    className={`px-4 py-2 rounded-lg text-sm transition ${
                      taskType === t
                        ? "bg-blue-600 text-white"
                        : "bg-zinc-800 text-zinc-400 hover:bg-zinc-700"
                    }`}
                  >
                    {t.charAt(0).toUpperCase() + t.slice(1)}
                  </button>
                ))}
              </div>
            </div>

            {taskType === "shell" && (
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Command</label>
                <input
                  type="text"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="echo 'Hello from Jarvis'"
                  className="w-full bg-zinc-800 text-white px-3 py-2 rounded-lg border border-zinc-700 focus:border-blue-500 focus:outline-none font-mono text-sm"
                />
              </div>
            )}

            {taskType === "conversation" && (
              <div>
                <label className="block text-sm text-zinc-400 mb-1">Message</label>
                <textarea
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  placeholder="Summarize today's system health"
                  rows={3}
                  className="w-full bg-zinc-800 text-white px-3 py-2 rounded-lg border border-zinc-700 focus:border-blue-500 focus:outline-none"
                />
              </div>
            )}

            <button
              onClick={handleCreate}
              disabled={!name.trim()}
              className="px-4 py-2 bg-blue-600 rounded-lg hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
            >
              Create Schedule
            </button>
          </div>
        )}

        {/* Schedule List */}
        {schedules.length === 0 && !showCreate && (
          <div className="text-center py-16 text-zinc-500">
            <p className="text-lg mb-2">No scheduled tasks yet</p>
            <p className="text-sm">Create a schedule to automate recurring tasks</p>
          </div>
        )}

        <div className="space-y-3">
          {schedules.map((s) => (
            <div
              key={s.schedule_id}
              className={`bg-zinc-900 rounded-xl p-4 border transition ${
                s.enabled
                  ? "border-zinc-800"
                  : "border-zinc-800/50 opacity-60"
              }`}
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-3 mb-1">
                    <h3 className="font-semibold">{s.name}</h3>
                    <span className={`px-2 py-0.5 rounded text-xs ${
                      s.enabled
                        ? "bg-green-900/50 text-green-300"
                        : "bg-zinc-800 text-zinc-500"
                    }`}>
                      {s.enabled ? "Active" : "Paused"}
                    </span>
                    {s.last_status === "failed" && (
                      <span className="px-2 py-0.5 rounded text-xs bg-red-900/50 text-red-300">
                        Failed
                      </span>
                    )}
                  </div>
                  <div className="flex items-center gap-4 text-sm text-zinc-400">
                    <span className="font-mono bg-zinc-800 px-2 py-0.5 rounded text-xs">
                      {s.cron}
                    </span>
                    <span>{s.task_type}</span>
                    <span>{s.run_count} runs</span>
                    {s.last_run && (
                      <span>Last: {new Date(s.last_run).toLocaleString()}</span>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => toggleEnabled(s)}
                    className={`px-3 py-1 rounded text-xs ${
                      s.enabled
                        ? "bg-zinc-800 text-zinc-300 hover:bg-zinc-700"
                        : "bg-green-900/50 text-green-300 hover:bg-green-900"
                    }`}
                  >
                    {s.enabled ? "Pause" : "Resume"}
                  </button>
                  <button
                    onClick={() => handleDelete(s.schedule_id)}
                    className="px-3 py-1 bg-red-900/50 text-red-300 rounded text-xs hover:bg-red-900"
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
