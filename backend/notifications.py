"""
Outbound notifications — how the AI / app reaches a person.

One entry point, `notify(user, subject, message)`, with the channel chosen by the
NOTIFY_CHANNEL env var. The channel is deliberately abstracted so we can plug in
WeChat Work, Twilio SMS, or Teams later without touching call sites.

  NOTIFY_CHANNEL=console      (default) — just prints; safe for dev
  NOTIFY_CHANNEL=wechat_work  — WeChat Work (企业微信). NOTE: consumer/personal
                                WeChat has no official bot API; this is the
                                company edition. Needs WECOM_* env vars.
  NOTIFY_CHANNEL=twilio       — SMS. Needs TWILIO_* env vars + user phone.
  NOTIFY_CHANNEL=teams        — Microsoft Teams incoming webhook. Needs TEAMS_WEBHOOK_URL.

All senders are best-effort: failures are logged, never raised, so a missing key
can't break a task assignment.
"""

import os

import httpx


def notify(user: dict, subject: str, message: str) -> None:
    channel = os.environ.get("NOTIFY_CHANNEL", "console").lower()
    try:
        if channel == "console":
            print(f"[notify→{user.get('email','?')}] {subject} — {message}")
        elif channel == "wechat_work":
            _send_wechat_work(user, subject, message)
        elif channel == "twilio":
            _send_twilio(user, subject, message)
        elif channel == "teams":
            _send_teams(user, subject, message)
        else:
            print(f"[notify] unknown NOTIFY_CHANNEL='{channel}', message dropped: {subject}")
    except Exception as e:  # never let a notification failure bubble up
        print(f"[notify] send failed via {channel}: {e}")


# --- Channel stubs (fill the env vars when a channel is chosen) -------------

def _send_wechat_work(user: dict, subject: str, message: str) -> None:
    corp_id = os.environ.get("WECOM_CORP_ID", "")
    agent_id = os.environ.get("WECOM_AGENT_ID", "")
    secret = os.environ.get("WECOM_SECRET", "")
    if not (corp_id and agent_id and secret):
        print("[notify] wechat_work not configured (WECOM_CORP_ID / WECOM_AGENT_ID / WECOM_SECRET)")
        return
    # Get an access token, then post a text message to the user.
    tok = httpx.get(
        "https://qyapi.weixin.qq.com/cgi-bin/gettoken",
        params={"corpid": corp_id, "corpsecret": secret}, timeout=15,
    ).json().get("access_token")
    if not tok:
        print("[notify] wechat_work: could not get access_token")
        return
    # touser should be the person's WeCom user id; we map from email for now.
    touser = user.get("wecom_userid") or user.get("email", "").split("@")[0]
    httpx.post(
        "https://qyapi.weixin.qq.com/cgi-bin/message/send",
        params={"access_token": tok},
        json={"touser": touser, "msgtype": "text", "agentid": agent_id,
              "text": {"content": f"{subject}\n{message}"}},
        timeout=15,
    )


def _send_twilio(user: dict, subject: str, message: str) -> None:
    sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
    token = os.environ.get("TWILIO_AUTH_TOKEN", "")
    from_num = os.environ.get("TWILIO_FROM", "")
    to_num = user.get("phone", "")
    if not (sid and token and from_num and to_num):
        print("[notify] twilio not configured (TWILIO_* env or user has no phone)")
        return
    httpx.post(
        f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json",
        data={"From": from_num, "To": to_num, "Body": f"{subject}: {message}"},
        auth=(sid, token), timeout=15,
    )


def _send_teams(user: dict, subject: str, message: str) -> None:
    webhook = os.environ.get("TEAMS_WEBHOOK_URL", "")
    if not webhook:
        print("[notify] teams not configured (TEAMS_WEBHOOK_URL)")
        return
    httpx.post(webhook, json={"title": subject, "text": message}, timeout=15)
