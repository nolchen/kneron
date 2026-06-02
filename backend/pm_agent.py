"""
Program Manager Agent — calls Ollama directly via the OpenAI-compatible SDK.
(Hermes Agent is still cloned for reference but we skip its complex init pipeline.)
"""

import json
import os
from typing import Optional, List, Dict

from openai import OpenAI

OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1")
DEFAULT_MODEL   = os.environ.get("OLLAMA_MODEL", "llama3.2")

PM_SYSTEM_PROMPT = """\
You are an expert AI Program Manager with access to a team's GitHub data. \
Help engineering teams stay organised, prioritise work, and ship on time.

When analysing data:
- Assess each team member's workload (open issues + PRs + recent commits).
- Flag members who appear overloaded (workload_score > 10) or have no recent activity.
- Prioritise issues by labels: blocker > priority-high > bug > priority-medium > others.
- Surface at-risk milestones (low progress with a close due date).
- Identify stale PRs (open > 7 days with no update).
- Give concrete, actionable recommendations — name specific people and issue/PR numbers.
- Keep responses concise: use bullet points and short paragraphs.
- Do NOT mention being an AI or any disclaimers. Just answer directly."""


class ProgramManagerAgent:
    def __init__(self, model: str = DEFAULT_MODEL):
        self.model  = model
        self.client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

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
                "top_issues": github_context.get("issues", [])[:10],
                "open_prs": github_context.get("pull_requests", [])[:10],
            }
            messages.append({
                "role": "user",
                "content": f"Here is the current GitHub snapshot:\n```json\n{json.dumps(summary, indent=2, default=str)}\n```",
            })
            messages.append({
                "role": "assistant",
                "content": "Got it — I have the GitHub data loaded. What would you like to know?",
            })

        # Inject relevant past notes/reports as context
        if notes_context:
            notes_text = "\n\n".join(
                f"[{n['type'].upper()} — {n['title']} — {n['created_at'][:10]}]\n{n['content']}"
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
