"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Users, Map, ListOrdered,
  MessageSquare, Bot, CalendarDays, ClipboardList,
  Sun, Moon, BookOpen, Mail, ShieldCheck, Inbox,
} from "lucide-react";
import { useTheme } from "@/lib/useTheme";
import { useAuth } from "@/lib/auth";
import AuthBox from "@/components/AuthBox";

const NAV = [
  { href: "/",             label: "Dashboard",    icon: LayoutDashboard },
  { href: "/team",         label: "Team",          icon: Users },
  { href: "/assignments",  label: "Assignments",   icon: ClipboardList },
  { href: "/inbox",        label: "My Tasks",      icon: Inbox },
  { href: "/roadmap",      label: "Timeline",      icon: Map },
  { href: "/priorities",   label: "Priorities",    icon: ListOrdered },
  { href: "/calendar",     label: "Calendar",      icon: CalendarDays },
  { href: "/reports",      label: "Reports",       icon: BookOpen },
  { href: "/email",        label: "Email",         icon: Mail },
  { href: "/chat",         label: "AI PM Chat",    icon: MessageSquare },
];

export default function Sidebar() {
  const path       = usePathname();
  const { dark, toggle } = useTheme();
  const { user, enforced } = useAuth();

  // Admin nav appears for admins (and in open demo mode, for setup).
  const nav = (!enforced || user?.role === "admin")
    ? [...NAV, { href: "/admin", label: "Users & Roles", icon: ShieldCheck }]
    : NAV;

  return (
    <aside className="flex h-screen w-60 shrink-0 flex-col bg-sidebar text-white">
      <div className="flex items-center gap-2 px-5 py-5 border-b border-white/10">
        <Bot className="h-6 w-6 text-brand-purple" />
        <span className="font-bold text-lg tracking-tight">PM Agent</span>
      </div>

      <nav className="flex flex-col gap-1 px-3 py-4 flex-1">
        {nav.map(({ href, label, icon: Icon }) => {
          const active = path === href;
          return (
            <Link
              key={href}
              href={href}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                active
                  ? "bg-brand-purple text-white"
                  : "text-white/60 hover:bg-white/10 hover:text-white"
              }`}
            >
              <Icon className="h-4 w-4" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Dark mode toggle */}
      <div className="px-4 pb-3">
        <button
          onClick={toggle}
          className="flex items-center gap-2 w-full rounded-lg px-3 py-2 text-sm text-white/50 hover:bg-white/10 hover:text-white transition-colors"
        >
          {dark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          {dark ? "Light mode" : "Dark mode"}
        </button>
      </div>

      <AuthBox />

      <div className="px-5 py-3 border-t border-white/10 text-xs text-white/25">
        Powered by Hermes Agent
      </div>
    </aside>
  );
}
