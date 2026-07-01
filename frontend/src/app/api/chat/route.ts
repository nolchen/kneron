import { proxy } from "@/lib/proxy";

export const runtime = "nodejs";
export const maxDuration = 60;

export async function POST(req: Request) {
  return proxy(req, "/api/chat");
}
