import { NextRequest, NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";
export const maxDuration = 60;

type Msg = { role: "user" | "assistant"; content: string };

function modelChatUrl(value: string) {
  const trimmed = value.trim().replace(/\/+$/, "");
  if (trimmed.endsWith("/v1/chat/completions")) return trimmed;
  if (trimmed.endsWith("/chat/completions")) return trimmed;
  const base = trimmed.replace(/\/(health|v1\/models)$/, "");
  return base + "/v1/chat/completions";
}

function extractContent(payload: any): string | null {
  const value =
    payload?.choices?.[0]?.message?.content ??
    payload?.choices?.[0]?.text ??
    payload?.message?.content ??
    payload?.message ??
    payload?.response ??
    payload?.output;
  if (typeof value === "string") return value.trim() || null;
  if (Array.isArray(value)) {
    const text = value
      .map((part) => typeof part === "string" ? part : typeof part?.text === "string" ? part.text : "")
      .filter(Boolean)
      .join("");
    return text.trim() || null;
  }
  return null;
}

const json = (body: unknown, status = 200) =>
  NextResponse.json(body, { status, headers: { "Cache-Control": "no-store, max-age=0" } });

export async function POST(request: NextRequest) {
  const supabase = await createClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();
  if (authError || !user) return json({ error: "로그인이 필요합니다." }, 401);

  let body: { messages?: Msg[]; conversationId?: string };
  try {
    body = await request.json();
  } catch {
    return json({ error: "요청 형식이 올바르지 않습니다." }, 400);
  }

  if (!Array.isArray(body.messages) || body.messages.length === 0) {
    return json({ error: "메시지가 비어 있습니다." }, 400);
  }
  const messages = body.messages
    .filter((message): message is Msg =>
      !!message &&
      (message.role === "user" || message.role === "assistant") &&
      typeof message.content === "string" &&
      message.content.trim().length > 0
    )
    .slice(-24);

  if (!messages.length || messages.at(-1)?.role !== "user") {
    return json({ error: "마지막 메시지는 사용자 입력이어야 합니다." }, 400);
  }
  if (messages.some((message) => message.content.length > 16000)) {
    return json({ error: "메시지가 너무 깁니다." }, 413);
  }

  let conversationId = body.conversationId;
  if (conversationId) {
    const { data, error } = await supabase
      .from("conversations")
      .select("id")
      .eq("id", conversationId)
      .eq("user_id", user.id)
      .maybeSingle();
    if (error || !data) return json({ error: "대화를 찾을 수 없습니다." }, 404);
  } else {
    const title = messages.filter((message) => message.role === "user").at(-1)?.content.slice(0, 80) ?? "새 대화";
    const { data, error } = await supabase
      .from("conversations")
      .insert({ user_id: user.id, title })
      .select("id")
      .single();
    if (error || !data) return json({ error: "대화를 저장하지 못했습니다." }, 500);
    conversationId = data.id;
  }

  const latest = messages.at(-1)!;
  const { error: userSaveError } = await supabase.from("messages").insert({
    conversation_id: conversationId,
    user_id: user.id,
    role: "user",
    content: latest.content,
  });
  if (userSaveError) return json({ error: "사용자 메시지를 저장하지 못했습니다." }, 500);

  const endpoint = process.env.AURA_MODEL_API_URL || process.env.AURA_INFERENCE_URL || "";
  // Prefer the gateway secret used by the Kaggle runtime when both names exist.
  const key = process.env.AURA_GATEWAY_SECRET || process.env.AURA_MODEL_API_KEY || "";
  if (!endpoint) return json({ error: "모델 추론 서버 주소가 설정되지 않았습니다.", conversationId }, 503);

  try {
    const upstream = await fetch(modelChatUrl(endpoint), {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(key ? { Authorization: `Bearer ${key}` } : {}),
      },
      body: JSON.stringify({
        model: "aura",
        messages,
        stream: false,
        max_tokens: 384,
        temperature: 0.55,
      }),
      cache: "no-store",
      signal: AbortSignal.timeout(55000),
    });

    const raw = await upstream.text();
    let payload: any = null;
    try { payload = raw ? JSON.parse(raw) : null; } catch { /* handled below */ }

    if (!upstream.ok) {
      const detail = payload?.detail || payload?.error?.message || `HTTP ${upstream.status}`;
      console.error("[Aura chat] inference upstream failed", { status: upstream.status, detail: String(detail).slice(0, 300) });
      return json({ error: "모델 서버 요청에 실패했습니다. 잠시 후 다시 시도해 주세요.", conversationId }, 502);
    }

    const content = extractContent(payload);
    if (!content) {
      console.error("[Aura chat] inference returned no text", { responseKeys: payload && typeof payload === "object" ? Object.keys(payload) : [] });
      return json({ error: "모델 서버에서 답변 텍스트를 받지 못했습니다.", conversationId }, 502);
    }

    const { error: assistantSaveError } = await supabase.from("messages").insert({
      conversation_id: conversationId,
      user_id: user.id,
      role: "assistant",
      content,
    });
    if (assistantSaveError) {
      console.error("[Aura chat] assistant message save failed", assistantSaveError.message);
      return json({ error: "AI 답변 저장에 실패했습니다.", conversationId }, 500);
    }

    await supabase.from("conversations")
      .update({ updated_at: new Date().toISOString() })
      .eq("id", conversationId)
      .eq("user_id", user.id);

    return json({ content, conversationId });
  } catch (error) {
    const timedOut = error instanceof Error && error.name === "TimeoutError";
    console.error("[Aura chat] inference request failed", timedOut ? "timeout" : error instanceof Error ? error.message : "unknown");
    return json({
      error: timedOut ? "모델 응답 시간이 초과되었습니다." : "모델 서버에 연결할 수 없습니다.",
      conversationId,
    }, 502);
  }
}
