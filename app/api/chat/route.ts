import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

type Msg = { role: "user" | "assistant"; content: string };

function modelChatUrl(value: string) {
  const trimmed = value.trim().replace(/\/+$/, "");
  if (trimmed.endsWith("/v1/chat/completions") || trimmed.endsWith("/chat/completions")) return trimmed;
  const base = trimmed.replace(/\/(health|v1\/models)$/, "");
  return base + "/v1/chat/completions";
}

function extractContent(payload: unknown): string | null {
  const root = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
  const choices = Array.isArray(root.choices) ? root.choices : [];
  const first = choices[0] && typeof choices[0] === "object" ? choices[0] as Record<string, unknown> : {};
  const message = first.message && typeof first.message === "object" ? first.message as Record<string, unknown> : {};
  const rootMessage = root.message && typeof root.message === "object" ? root.message as Record<string, unknown> : {};
  const value = message.content ?? first.text ?? rootMessage.content ??
    root.message ?? root.response ?? root.output;
  if (typeof value === "string") return value.trim() || null;
  if (Array.isArray(value)) {
    const text = value.map((part) => {
      if (typeof part === "string") return part;
      if (part && typeof part === "object" && "text" in part && typeof part.text === "string") return part.text;
      return "";
    }).filter(Boolean).join("");
    return text.trim() || null;
  }
  return null;
}

const json = (body: unknown, status = 200) =>
  NextResponse.json(body, { status, headers: { "Cache-Control": "no-store, max-age=0" } });

export async function POST(request: NextRequest) {
  let body: { messages?: Msg[]; conversationId?: string };
  try { body = await request.json(); }
  catch { return json({ error: "요청 형식이 올바르지 않습니다." }, 400); }

  if (!Array.isArray(body.messages) || body.messages.length === 0) {
    return json({ error: "메시지가 비어 있습니다." }, 400);
  }
  const messages = body.messages.filter((message): message is Msg =>
    !!message && (message.role === "user" || message.role === "assistant") &&
    typeof message.content === "string" && message.content.trim().length > 0
  ).slice(-24);

  if (!messages.length || messages.at(-1)?.role !== "user") {
    return json({ error: "마지막 메시지는 사용자 입력이어야 합니다." }, 400);
  }
  if (messages.some((message) => message.content.length > 16000)) {
    return json({ error: "메시지가 너무 깁니다." }, 413);
  }

  // Authentication is optional. Signed-in conversations are stored privately;
  // guest conversations are processed without creating a database record.
  let user: { id: string } | null = null;
  let supabase: Awaited<ReturnType<typeof createClient>> | null = null;
  try {
    supabase = await createClient();
    const { data } = await supabase.auth.getUser();
    user = data.user ? { id: data.user.id } : null;
  } catch (error) {
    console.warn("[Aura chat] auth lookup unavailable; continuing as guest",
      error instanceof Error ? error.message : "unknown");
  }

  let conversationId: string | undefined;
  const latest = messages.at(-1)!;

  if (user && supabase) {
    if (body.conversationId) {
      const { data, error } = await supabase.from("conversations")
        .select("id").eq("id", body.conversationId).eq("user_id", user.id).maybeSingle();
      if (error || !data) return json({ error: "대화를 찾을 수 없습니다." }, 404);
      conversationId = data.id;
    } else {
      const { data, error } = await supabase.from("conversations")
        .insert({ user_id: user.id, title: latest.content.slice(0, 80) || "새 대화" })
        .select("id").single();
      if (error || !data) {
        console.error("[Aura chat] conversation create failed", error?.message ?? "empty result");
        return json({ error: "대화를 저장하지 못했습니다." }, 500);
      }
      conversationId = data.id;
    }

    const { error: saveError } = await supabase.from("messages").insert({
      conversation_id: conversationId, user_id: user.id, role: "user", content: latest.content,
    });
    if (saveError) return json({ error: "사용자 메시지를 저장하지 못했습니다.", conversationId }, 500);
    await supabase.from("conversations").update({ updated_at: new Date().toISOString() })
      .eq("id", conversationId).eq("user_id", user.id);
  }

  const endpoint = process.env.AURA_MODEL_API_URL || process.env.AURA_INFERENCE_URL || "";
  const key = process.env.AURA_GATEWAY_SECRET || process.env.AURA_MODEL_API_KEY || "";
  if (!endpoint) return json({ error: "모델 추론 서버 주소가 설정되지 않았습니다.", ...(conversationId ? { conversationId } : {}) }, 503);

  try {
    const upstream = await fetch(modelChatUrl(endpoint), {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(key ? { Authorization: `Bearer ${key}` } : {}) },
      body: JSON.stringify({ model: "aura", messages, stream: false, max_tokens: 160, temperature: 0.55 }),
      cache: "no-store",
      signal: AbortSignal.timeout(55000),
    });
    const raw = await upstream.text();
    let payload: unknown = null;
    try { payload = raw ? JSON.parse(raw) as unknown : null; } catch { /* handled below */ }

    if (!upstream.ok) {
      const errorBody = payload && typeof payload === "object" ? payload as Record<string, unknown> : {};
      const errorInfo = errorBody.error && typeof errorBody.error === "object"
        ? errorBody.error as Record<string, unknown> : {};
      console.error("[Aura chat] inference upstream failed", {
        status: upstream.status, detail: String(errorBody.detail || errorInfo.message || `HTTP ${upstream.status}`).slice(0, 300),
      });
      return json({ error: upstream.status === 403
        ? "모델 서버 인증이 거부되었습니다. 운영 설정을 확인 중입니다."
        : "모델 서버 요청에 실패했습니다. 잠시 후 다시 시도해 주세요.",
        ...(conversationId ? { conversationId } : {}) }, 502);
    }

    const content = extractContent(payload);
    if (!content) return json({ error: "모델 서버에서 답변 텍스트를 받지 못했습니다.", ...(conversationId ? { conversationId } : {}) }, 502);

    if (user && supabase && conversationId) {
      const { error } = await supabase.from("messages").insert({
        conversation_id: conversationId, user_id: user.id, role: "assistant", content,
      });
      if (error) {
        console.error("[Aura chat] assistant message save failed", error.message);
        return json({ error: "AI 답변 저장에 실패했습니다.", conversationId }, 500);
      }
      await supabase.from("conversations").update({ updated_at: new Date().toISOString() })
        .eq("id", conversationId).eq("user_id", user.id);
    }

    return json({ content, ...(conversationId ? { conversationId } : {}) });
  } catch (error) {
    const timedOut = error instanceof Error && error.name === "TimeoutError";
    console.error("[Aura chat] inference request failed", timedOut ? "timeout" : error instanceof Error ? error.message : "unknown");
    return json({ error: timedOut ? "모델 응답 시간이 초과되었습니다." : "모델 서버에 연결할 수 없습니다.",
      ...(conversationId ? { conversationId } : {}) }, 502);
  }
}
