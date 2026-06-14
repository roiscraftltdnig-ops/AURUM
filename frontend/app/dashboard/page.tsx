"use client";

import { useEffect, useMemo, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { AlertTriangle, Bell, FileUp, Filter, Radio, Search, Send, Users, type LucideIcon } from "lucide-react";
import { apiFetch } from "@/lib/api";
import { Badge, Button, Card } from "@/components/ui";

type User = {
  id: string;
  telegram_username?: string;
  first_name?: string;
  qualification_stage: string;
  lead_temperature: string;
  engagement_score: number;
  followup_required: boolean;
  last_seen_at?: string;
};

type Task = {
  id: string;
  title: string;
  summary: string;
  priority: string;
  recommended_action: string;
  created_at: string;
};

type CommunityGroup = {
  id?: string;
  key: string;
  portfolio: string;
  label: string;
  invite_url: string;
  min_stage: string;
  is_vip: boolean;
  is_active: boolean;
};

type ContentAudit = {
  ok: boolean;
  checked_at: string;
  missing: Array<{ key: string; label: string; type: string }>;
  documents_checked: number;
  resources_checked: number;
};

export default function DashboardPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [groups, setGroups] = useState<CommunityGroup[]>([]);
  const [metrics, setMetrics] = useState<Record<string, number>>({});
  const [contentAudit, setContentAudit] = useState<ContentAudit | null>(null);
  const [filter, setFilter] = useState("");
  const [broadcast, setBroadcast] = useState("");
  const [portfolio, setPortfolio] = useState("Aurum Foundation");
  const [groupDraft, setGroupDraft] = useState<CommunityGroup>({
    key: "aurum_intro_video",
    portfolio: "Aurum Foundation",
    label: "Aurum Introduction Video",
    invite_url: "",
    min_stage: "BEGINNER",
    is_vip: false,
    is_active: true
  });
  const [uploading, setUploading] = useState(false);

  async function load() {
    try {
      const [loadedUsers, loadedTasks, loadedMetrics, loadedGroups, loadedAudit] = await Promise.all([
        apiFetch<User[]>("/admin/users"),
        apiFetch<Task[]>("/admin/tasks"),
        apiFetch<Record<string, number>>("/admin/metrics"),
        apiFetch<CommunityGroup[]>("/admin/community-groups"),
        apiFetch<ContentAudit>("/admin/content-audit")
      ]);
      setUsers(loadedUsers);
      setTasks(loadedTasks);
      setMetrics(loadedMetrics);
      setGroups(loadedGroups);
      setContentAudit(loadedAudit);
    } catch {
      window.location.href = "/login";
    }
  }

  useEffect(() => {
    load();
  }, []);

  const filteredUsers = useMemo(() => {
    const needle = filter.toLowerCase();
    return users.filter((user) => [user.telegram_username, user.first_name, user.qualification_stage, user.lead_temperature].join(" ").toLowerCase().includes(needle));
  }, [filter, users]);

  async function uploadDocument(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setUploading(true);
    const form = new FormData();
    form.append("file", file);
    form.append("portfolio", portfolio);
    const token = localStorage.getItem("roiscraft_token");
    await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/admin/documents`, {
      method: "POST",
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: form
    });
    setUploading(false);
  }

  async function sendBroadcast() {
    if (!broadcast.trim()) return;
    await apiFetch("/admin/broadcasts", {
      method: "POST",
      body: JSON.stringify({ title: "Admin broadcast", body: broadcast, segment: { stage: "all" }, status: "scheduled" })
    });
    setBroadcast("");
  }

  async function saveGroup() {
    await apiFetch("/admin/community-groups", {
      method: "POST",
      body: JSON.stringify(groupDraft)
    });
    await load();
  }

  async function triggerDailyReport() {
    await apiFetch("/admin/reports/daily", { method: "POST" });
  }

  async function exportCsv() {
    const token = localStorage.getItem("roiscraft_token");
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000"}/admin/users/export.csv`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    });
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = "roiscraft-users.csv";
    anchor.click();
    URL.revokeObjectURL(url);
  }

  const cards: Array<[string, string | number, LucideIcon]> = [
    ["Total users", metrics.total_users ?? users.length, Users],
    ["Hot leads", metrics.hot_leads ?? users.filter((u) => u.lead_temperature === "HOT").length, Bell],
    ["Action queue", metrics.open_tasks ?? tasks.length, Filter],
    ["VIP requests", metrics.vip_requests ?? 0, Radio]
  ];

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top_left,rgba(216,178,93,0.12),transparent_34%),#07080d]">
      <div className="mx-auto flex max-w-7xl flex-col gap-6 px-5 py-6">
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="text-sm text-gold">Telegram-native ecosystem operating system</p>
            <h1 className="text-3xl font-semibold">ROISCRAFT Intelligence</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button className="bg-mint text-ink hover:bg-[#6ee4b8]" onClick={exportCsv}>Export CSV</Button>
            <Button className="bg-coral text-ink hover:bg-[#ff8d80]" onClick={triggerDailyReport}>Daily report</Button>
            <Button onClick={() => apiFetch("/admin/telegram/webhook", { method: "POST" })}>Activate webhook</Button>
          </div>
        </header>

        <section className="grid gap-4 md:grid-cols-4">
          {cards.map(([label, value, Icon]) => (
            <Card key={String(label)} className="p-4">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-400">{String(label)}</p>
                <Icon className="h-4 w-4 text-gold" />
              </div>
              <p className="mt-3 text-3xl font-semibold">{String(value)}</p>
            </Card>
          ))}
        </section>

        {contentAudit && !contentAudit.ok && (
          <Card className="border-coral/50 bg-coral/10 p-4">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-1 h-5 w-5 shrink-0 text-coral" />
              <div>
                <h2 className="text-lg font-semibold">Missing Aurum resources</h2>
                <p className="mt-1 text-sm text-slate-300">These Aurum PDFs or video links are required before the assistant can answer confidently.</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  {contentAudit.missing.map((item) => (
                    <Badge key={item.key} tone="hot">{item.label}</Badge>
                  ))}
                </div>
              </div>
            </div>
          </Card>
        )}

        <section className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
          <Card className="p-4">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
              <div>
                <h2 className="text-lg font-semibold">Telegram CRM</h2>
                <p className="text-sm text-slate-400">Search, qualify, and prioritize ecosystem participants.</p>
              </div>
              <label className="flex h-10 items-center gap-2 rounded-md border border-line bg-ink px-3">
                <Search className="h-4 w-4 text-slate-500" />
                <input className="w-56 bg-transparent text-sm outline-none" placeholder="Search users" value={filter} onChange={(e) => setFilter(e.target.value)} />
              </label>
            </div>
            <div className="overflow-hidden rounded-lg border border-line">
              <table className="w-full text-left text-sm">
                <thead className="bg-ink text-slate-400">
                  <tr>
                    <th className="p-3">User</th>
                    <th className="p-3">Stage</th>
                    <th className="p-3">Temperature</th>
                    <th className="p-3">Score</th>
                    <th className="p-3">Follow-up</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((user) => (
                    <tr key={user.id} className="border-t border-line">
                      <td className="p-3">@{user.telegram_username || user.first_name || "telegram-user"}</td>
                      <td className="p-3">{user.qualification_stage}</td>
                      <td className="p-3"><Badge tone={user.lead_temperature === "HOT" ? "hot" : user.lead_temperature === "WARM" ? "warm" : "cold"}>{user.lead_temperature}</Badge></td>
                      <td className="p-3">{user.engagement_score || 0}</td>
                      <td className="p-3">{user.followup_required ? "Required" : "Nurture"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          <div className="space-y-6">
            <Card className="p-4">
              <h2 className="text-lg font-semibold">Action required</h2>
              <div className="mt-4 space-y-3">
                <AnimatePresence>
                  {tasks.slice(0, 5).map((task) => (
                    <motion.div key={task.id} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="rounded-md border border-line bg-ink p-3">
                      <div className="flex items-center justify-between gap-2">
                        <p className="font-medium">{task.title}</p>
                        <Badge tone="hot">{task.priority}</Badge>
                      </div>
                      <p className="mt-2 text-sm text-slate-400">{task.summary}</p>
                      <p className="mt-2 text-sm text-gold">{task.recommended_action}</p>
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </Card>

            <Card className="p-4">
              <h2 className="text-lg font-semibold">Knowledge upload</h2>
              <div className="mt-4 flex gap-2">
                <select className="h-10 rounded-md border border-line bg-ink px-3 text-sm" value={portfolio} onChange={(e) => setPortfolio(e.target.value)}>
                  <option>Aurum Foundation</option>
                </select>
                <label className="inline-flex h-10 cursor-pointer items-center gap-2 rounded-md border border-line px-3 text-sm">
                  <FileUp className="h-4 w-4" />
                  {uploading ? "Processing..." : "Upload"}
                  <input className="hidden" type="file" accept=".pdf,.docx,.txt,.md,.markdown" onChange={uploadDocument} />
                </label>
              </div>
            </Card>

            <Card className="p-4">
              <h2 className="text-lg font-semibold">Aurum resource center</h2>
              <div className="mt-4 grid gap-2">
                <input className="h-10 rounded-md border border-line bg-ink px-3 text-sm outline-none focus:border-gold" placeholder="Resource key, e.g. aurum_intro_video" value={groupDraft.key} onChange={(e) => setGroupDraft({ ...groupDraft, key: e.target.value })} />
                <input className="h-10 rounded-md border border-line bg-ink px-3 text-sm outline-none focus:border-gold" placeholder="Label" value={groupDraft.label} onChange={(e) => setGroupDraft({ ...groupDraft, label: e.target.value })} />
                <input className="h-10 rounded-md border border-line bg-ink px-3 text-sm outline-none focus:border-gold" placeholder="PDF, video, booking, support, or Telegram URL" value={groupDraft.invite_url} onChange={(e) => setGroupDraft({ ...groupDraft, invite_url: e.target.value })} />
                <div className="grid grid-cols-2 gap-2">
                  <select className="h-10 rounded-md border border-line bg-ink px-3 text-sm" value={groupDraft.portfolio} onChange={(e) => setGroupDraft({ ...groupDraft, portfolio: e.target.value })}>
                    <option>Aurum Foundation</option>
                  </select>
                  <select className="h-10 rounded-md border border-line bg-ink px-3 text-sm" value={groupDraft.min_stage} onChange={(e) => setGroupDraft({ ...groupDraft, min_stage: e.target.value })}>
                    <option>BEGINNER</option>
                    <option>INTERMEDIATE</option>
                    <option>ADVANCED</option>
                    <option>HIGH_INTENT</option>
                  </select>
                </div>
                <Button onClick={saveGroup}>Save resource</Button>
              </div>
              <div className="mt-4 space-y-2">
                {groups.slice(0, 4).map((group) => (
                  <div className="rounded-md border border-line bg-ink p-2 text-sm" key={group.id || group.key}>
                    <div className="flex items-center justify-between gap-2">
                      <span>{group.label}</span>
                      <Badge tone={group.min_stage === "HIGH_INTENT" ? "hot" : "default"}>{group.min_stage}</Badge>
                    </div>
                    <p className="mt-1 truncate text-slate-500">{group.portfolio}</p>
                  </div>
                ))}
              </div>
            </Card>

            <Card className="p-4">
              <h2 className="text-lg font-semibold">Broadcast composer</h2>
              <textarea className="mt-4 min-h-28 w-full rounded-md border border-line bg-ink p-3 text-sm outline-none focus:border-gold" placeholder="Write a segmented Telegram campaign..." value={broadcast} onChange={(e) => setBroadcast(e.target.value)} />
              <Button className="mt-3 gap-2" onClick={sendBroadcast}><Send className="h-4 w-4" /> Schedule broadcast</Button>
            </Card>
          </div>
        </section>
      </div>
    </main>
  );
}
