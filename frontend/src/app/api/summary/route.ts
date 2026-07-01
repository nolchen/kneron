import { proxy } from "@/lib/proxy";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function GET(req: Request) {
  return proxy(req, "/api/summary");
}
