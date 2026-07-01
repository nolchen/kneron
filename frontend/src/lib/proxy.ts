// Server-side proxy to the backend for slow/LLM endpoints.
//
// The next.config edge rewrite is unreliable for long requests (it randomly
// balloons a ~8s call to 20s+), which the browser reads as "Failed to fetch".
// Routing those endpoints through a Node serverless function instead is fast and
// consistent, and lets us set a real 60s budget. Keeps everything same-origin so
// the session cookie stays first-party.
const BACKEND = process.env.BACKEND_ORIGIN || "http://localhost:8000";

export async function proxy(req: Request, path: string): Promise<Response> {
  const method = req.method;
  const hasBody = method !== "GET" && method !== "HEAD";
  const res = await fetch(`${BACKEND}${path}`, {
    method,
    headers: {
      "content-type": req.headers.get("content-type") || "application/json",
      cookie: req.headers.get("cookie") || "",
    },
    body: hasBody ? await req.text() : undefined,
  });
  const headers = new Headers();
  const ct = res.headers.get("content-type");
  if (ct) headers.set("content-type", ct);
  return new Response(res.body, { status: res.status, headers });
}
