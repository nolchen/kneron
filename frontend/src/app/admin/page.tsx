"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { User, Role } from "@/lib/types";
import { useAuth } from "@/lib/auth";
import { RefreshCw, ShieldAlert, Users as UsersIcon } from "lucide-react";

const ROLES: Role[] = ["admin", "manager", "intern"];

export default function AdminPage() {
  const { user, enforced, loading: authLoading } = useAuth();
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [savingEmail, setSavingEmail] = useState("");

  const allowed = !enforced || user?.role === "admin";

  useEffect(() => {
    if (authLoading) return;
    if (!allowed) { setLoading(false); return; }
    api.listUsers()
      .then((r) => setUsers(r.users))
      .catch((e) => setError(e instanceof Error ? e.message : "Failed to load users"))
      .finally(() => setLoading(false));
  }, [authLoading, allowed]);

  const patch = (email: string, fields: Partial<User>) =>
    setUsers((prev) => prev.map((u) => (u.email === email ? { ...u, ...fields } : u)));

  const changeRole = async (email: string, role: Role) => {
    setSavingEmail(email);
    try { const u = await api.setUserRole(email, role); patch(email, u); }
    catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setSavingEmail(""); }
  };

  const changeManager = async (email: string, manager_email: string) => {
    setSavingEmail(email);
    try { const u = await api.setUserManager(email, manager_email); patch(email, u); }
    catch (e) { setError(e instanceof Error ? e.message : "Failed"); }
    finally { setSavingEmail(""); }
  };

  if (authLoading || loading)
    return <div className="flex h-full items-center justify-center"><RefreshCw className="h-6 w-6 animate-spin text-brand-purple" /></div>;

  if (!allowed)
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 text-text-3">
        <ShieldAlert className="h-10 w-10" />
        <p className="text-sm">Admins only.</p>
      </div>
    );

  const sel = "rounded-lg border border-ui-border bg-surface px-2 py-1.5 text-xs text-text-1 focus:outline-none focus:ring-2 focus:ring-brand-purple";

  return (
    <div className="p-8 max-w-4xl">
      <div className="flex items-center gap-2 mb-1">
        <UsersIcon className="h-5 w-5 text-brand-purple" />
        <h1 className="text-2xl font-bold text-text-1">Users &amp; Roles</h1>
      </div>
      <p className="text-sm text-text-2 mb-6">Set each person&apos;s permission level and who they report to. Reporting drives who can see whose work.</p>

      {error && <p className="text-xs text-red-500 mb-3">{error}</p>}

      <div className="bg-surface border border-ui-border rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-ui-border text-left text-xs uppercase tracking-wide text-text-3">
              <th className="px-4 py-3 font-semibold">Person</th>
              <th className="px-4 py-3 font-semibold">Role</th>
              <th className="px-4 py-3 font-semibold">Reports to</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ui-border">
            {users.map((u) => (
              <tr key={u.email} className={savingEmail === u.email ? "opacity-50" : ""}>
                <td className="px-4 py-3">
                  <p className="font-medium text-text-1">{u.name || u.email}</p>
                  <p className="text-xs text-text-3">{u.email}</p>
                </td>
                <td className="px-4 py-3">
                  <select className={sel} value={u.role} onChange={(e) => changeRole(u.email, e.target.value as Role)}>
                    {ROLES.map((r) => <option key={r} value={r}>{r}</option>)}
                  </select>
                </td>
                <td className="px-4 py-3">
                  <select className={sel} value={u.manager_email ?? ""} onChange={(e) => changeManager(u.email, e.target.value)}>
                    <option value="">— none —</option>
                    {users.filter((m) => m.email !== u.email).map((m) => (
                      <option key={m.email} value={m.email}>{m.name || m.email}</option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr><td colSpan={3} className="px-4 py-8 text-center text-text-3 text-sm">No users yet — they appear here after their first sign-in.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
