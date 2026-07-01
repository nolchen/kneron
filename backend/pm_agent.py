"""
Program Manager Agent — calls any OpenAI-compatible LLM (Ollama / Groq / OpenAI).
Provider is chosen via env vars; see llm_config.py.
"""

import json
from typing import Optional, List, Dict

from openai import OpenAI
from llm_config import llm_config


def _parse_json_array(text: str) -> List[Dict]:
    """Pull a JSON array out of an LLM response, tolerating code fences / stray prose."""
    if not text:
        return []
    start, end = text.find("["), text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        data = json.loads(text[start : end + 1])
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, ValueError):
        return []

PM_SYSTEM_PROMPT = """\
You are an expert AI Program Manager with access to a team's GitHub data. \
Help engineering teams stay organised, prioritise work, and ship on time.

When analysing data:
- Assess each team member's workload (open issues + PRs + recent commits).
- Flag members who appear overloaded (workload_score > 10) or have no recent activity.
- Prioritise issues by labels: blocker > priority-high > bug > priority-medium > others.
- Surface at-risk milestones (low progress with a close due date).
- Identify stale PRs (open > 7 days with no update).
- Use `current_assignments` (the live task board + calendar) to answer anything about
  tasks, deadlines, due dates, who is working on what, and what is overdue or due soon.
  This reflects the user's latest edits — always trust it over older data.
- When relevant past reports/notes are provided, reference them by title.
- Give concrete, actionable recommendations — name specific people and issue/PR numbers.
- Keep responses concise: use bullet points and short paragraphs.
- Do NOT mention being an AI or any disclaimers. Just answer directly."""


class ProgramManagerAgent:
    def __init__(self, model: Optional[str] = None):
        cfg = llm_config()
        self.provider = cfg["provider"]
        self.model    = model or cfg["model"]
        # api_key must be non-empty for the SDK; Ollama ignores it
        self.client = OpenAI(base_url=cfg["base_url"], api_key=cfg["api_key"] or "none")

    def _build_messages(
        self,
        user_message: str,
        github_context: Optional[Dict],
        conversation_history: Optional[List[Dict]],
        notes_context: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        messages = [{"role": "system", "content": PM_SYSTEM_PROMPT}]

        if github_context:
            summary = {
                "team_members": [
                    {
                        "login": m["login"],
                        "open_issues": m["open_issues"],
                        "open_prs": m["open_prs"],
                        "recent_commits": m["recent_commits"],
                        "workload_score": m["workload_score"],
                    }
                    for m in github_context.get("team_members", [])
                ],
                "projects": [
                    {
                        "repo": p["repo"],
                        "open_issues": p["open_issues_count"],
                        "open_prs": p["open_prs_count"],
                        "milestones": p.get("milestones", []),
                    }
                    for p in github_context.get("projects", [])
                ],
                # Slim to key fields — full issue/PR objects bloat the prompt
                # and can overflow the model's context.
                "top_issues": [
                    {"title": i.get("title"), "assignees": i.get("assignees"), "labels": i.get("labels")}
                    for i in github_context.get("issues", [])[:8]
                ],
                "open_prs": [
                    {"title": p.get("title"), "author": p.get("author")}
                    for p in github_context.get("pull_requests", [])[:8]
                ],
                "current_assignments": [
                    {
                        "title":     a.get("title"),
                        "assignees": a.get("assignees"),
                        "due_date":  a.get("due_date"),
                        "status":    a.get("status"),
                        "priority":  a.get("priority"),
                    }
                    for a in github_context.get("assignments", [])
                ],
            }
            messages.append({
                "role": "user",
                "content": (
                    "Here is the current team data — team workload, projects, issues, PRs, "
                    "and `current_assignments` (the live task board + calendar with due dates):\n"
                    f"```json\n{json.dumps(summary, indent=2, default=str)}\n```"
                ),
            })
            messages.append({
                "role": "assistant",
                "content": "Got it — I have the GitHub data loaded. What would you like to know?",
            })

        # Inject relevant past notes/reports as context
        if notes_context:
            notes_text = "\n\n".join(
                # Cap each note so a pile of long reports can't overflow the prompt.
                f"[{n['type'].upper()} — {n['title']} — {n['created_at'][:10]}]\n{n['content'][:700]}"
                for n in notes_context
            )
            messages.append({
                "role": "user",
                "content": f"Here are relevant past reports and notes for context:\n\n{notes_text}",
            })
            messages.append({
                "role": "assistant",
                "content": "Got it — I have those past reports loaded as context.",
            })

        for msg in (conversation_history or []):
            if msg.get("role") in ("user", "assistant"):
                messages.append({"role": msg["role"], "content": msg["content"]})

        messages.append({"role": "user", "content": user_message})
        return messages

    def chat(
        self,
        user_message: str,
        github_context: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None,
        notes_context: Optional[List[Dict]] = None,
    ) -> str:
        messages = self._build_messages(user_message, github_context, conversation_history, notes_context)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.4,
        )
        return response.choices[0].message.content or ""

    def stream_chat(
        self,
        user_message: str,
        github_context: Optional[Dict] = None,
        conversation_history: Optional[List[Dict]] = None,
        notes_context: Optional[List[Dict]] = None,
    ):
        """Yields text chunks as they arrive from Ollama."""
        messages = self._build_messages(user_message, github_context, conversation_history, notes_context)
        stream = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.4,
            stream=True,
        )
        for chunk in stream:
            delta = chunk.choices[0].delta.content
            if delta:
                yield delta

    def summarize_status(self, github_data: Dict) -> str:
        return self.chat(
            "Give me a concise executive summary (6–8 bullet points) covering: "
            "sprint health, biggest risks, milestone progress, and team health.",
            github_context=github_data,
        )

    def extract_events(self, emails_text: str, today_iso: str) -> List[Dict]:
        """Read email text and pull out calendar-worthy events (meetings, deadlines,
        calls, deliverables). Returns a list of dicts:
        {title, start, end, attendees, source_subject, confidence}.
        Datetimes are local ISO strings (no timezone) like '2026-06-20T14:00:00'.
        Best-effort: returns [] if nothing actionable or the model returns junk."""
        system = (
            "You extract calendar events from emails. Today is "
            f"{today_iso}. Resolve relative dates ('next Tuesday', 'tomorrow 3pm') to "
            "absolute local datetimes. Only include things that belong on a calendar: "
            "meetings, calls, deadlines, deliverables, interviews. Ignore newsletters, "
            "marketing, and vague mentions.\n"
            "Return ONLY a JSON array (no prose). Each item: "
            '{"title": str, "start": "YYYY-MM-DDTHH:MM:SS", "end": "YYYY-MM-DDTHH:MM:SS", '
            '"attendees": [email,...], "source_subject": str, "confidence": 0.0-1.0}. '
            "If a time is unknown, default to a 1-hour block at 09:00. Return [] if none."
        )
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": f"Emails:\n\n{emails_text}"},
            ],
            temperature=0,
        )
        return _parse_json_array(resp.choices[0].message.content or "")
