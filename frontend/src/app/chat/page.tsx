"use client";

import { useState, useRef, useEffect } from "react";
import { ChatMessage } from "@/lib/types";
import { Send, Bot, User, RefreshCw, Lightbulb } from "lucide-react";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const SUGGESTIONS = [
  "Who is overloaded on the team right now?",
  "What are the top 5 priorities this week?",
  "Which assignments are at risk of missing their deadline?",
  "Summarise the current status.",
  "Who has availability to take on more work?",
];

interface Bubble { role: "user" | "assistant"; content: string; streaming?: boolean; }

export default function ChatPage() {
  const [messages, setMessages] = useState<Bubble[]>([{
    role: "assistant",
    content: "Hi! I'm your AI Program Manager. I have access to your team data — ask me about workload, priorities, deadlines, or anything else.",
  }]);
  const [input, setInput]     = useState("");
  const [sending, setSending] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);
  const historyRef = useRef<ChatMessage[]>([]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const send = async (text: string) => {
    if (!text.trim() || sending) return;
    setSending(true); setInput("");
    setMessages((prev) => [...prev, { role: "user", content: text }, { role: "assistant", content: "", streaming: true }]);

    try {
      const res = await fetch(`${BASE}/api/chat/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, history: historyRef.current, include_github: true }),
      });
      if (!res.ok || !res.body) throw new Error("Stream failed");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let full = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        for (const line of decoder.decode(value, { stream: true }).split("\n")) {
          if (!line.startsWith("data: ")) continue;
          const payload = line.slice(6).trim();
          if (payload === "[DONE]") break;
          try {
            const { chunk } = JSON.parse(payload);
            full += chunk;
            setMessages((prev) => [...prev.slice(0, -1), { role: "assistant", content: full, streaming: true }]);
          } catch { /* partial chunk */ }
        }
      }

      setMessages((prev) => [...prev.slice(0, -1), { role: "assistant", content: full }]);
      historyRef.current = [...historyRef.current, { role: "user", content: text }, { role: "assistant", content: full }];
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : "Error";
      setMessages((prev) => [...prev.slice(0, -1), { role: "assistant", content: `Something went wrong: ${msg}` }]);
    } finally { setSending(false); }
  };

  return (
    <div className="flex flex-col h-full max-w-3xl mx-auto p-8 pb-0">
      <h1 className="text-2xl font-bold text-text-1 mb-1">AI PM Chat</h1>
      <p className="text-sm text-text-2 mb-4">Ask anything about your team, projects, or timeline.</p>

      <div className="flex flex-wrap gap-2 mb-4">
        {SUGGESTIONS.map((s) => (
          <button key={s} onClick={() => send(s)} disabled={sending}
            className="flex items-center gap-1.5 rounded-full border border-brand-purple/30 bg-surface px-3 py-1.5 text-xs text-text-2 hover:border-brand-purple hover:text-brand-purple transition-colors disabled:opacity-50">
            <Lightbulb className="h-3 w-3 text-brand-purple" />{s}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto flex flex-col gap-4 pr-1 pb-4">
        {messages.map((msg, i) => (
          <div key={i} className={`flex gap-3 ${msg.role === "user" ? "flex-row-reverse" : ""}`}>
            <div className={`shrink-0 h-8 w-8 rounded-full flex items-center justify-center text-white ${msg.role === "user" ? "bg-brand-dark" : "bg-brand-purple"}`}>
              {msg.role === "user" ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
            </div>
            <div className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed ${
              msg.role === "user"
                ? "bg-brand-dark text-white rounded-tr-sm"
                : "bg-surface border border-ui-border text-text-1 shadow-sm rounded-tl-sm"
            }`}>
              {msg.content === "" && msg.streaming ? (
                <span className="flex gap-1 items-center h-4">
                  {[0,150,300].map((d) => (
                    <span key={d} className="h-1.5 w-1.5 rounded-full bg-brand-purple animate-bounce" style={{ animationDelay: `${d}ms` }} />
                  ))}
                </span>
              ) : (
                <p className="whitespace-pre-line">
                  {msg.content}
                  {msg.streaming && <span className="inline-block w-0.5 h-3.5 bg-brand-purple ml-0.5 animate-pulse align-middle" />}
                </p>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="border-t border-ui-border bg-subtle py-4">
        <div className="flex gap-2">
          <input
            className="flex-1 rounded-xl border border-ui-border bg-surface px-4 py-3 text-sm text-text-1 focus:outline-none focus:ring-2 focus:ring-brand-purple"
            placeholder="Ask your program manager anything…"
            value={input} onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(input); } }}
          />
          <button onClick={() => send(input)} disabled={!input.trim() || sending}
            className="flex items-center justify-center h-12 w-12 rounded-xl bg-brand-purple text-white hover:opacity-90 disabled:opacity-50 transition-opacity shrink-0">
            {sending ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          </button>
        </div>
      </div>
    </div>
  );
}
