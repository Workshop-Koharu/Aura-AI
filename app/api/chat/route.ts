import { NextRequest, NextResponse } from "next/server";

type ChatMessage = { role: "user" | "assistant"; content: string };

export async function POST(request: NextRequest) {
  const endpoint = process.env.AURA_MODEL_API_URL;
  const apiKey = process.env.AURA_MODEL_API_KEY;
  if (!endpoint) {
    return NextResponse.json({ error: "모델 API 주소가 설정되지 않았습니다. AURA_MODEL_API_URL을 서버 환경 변수에 등록해 주세요." }, { status: 503 });
  }

  let messages: ChatMessage[];
  try {
    const body = await request.json();
    if (!Array.isArray(body.messages) || body.messages.length === 0) {
      return NextResponse.json({ error: "메시지가 비어 있습니다." }, { status: 400 });
    }
    messages = body.messages.filter((item: unknown): item is ChatMessage =>
      !!item && typeof item === "object" &&
      ["user", "assistant"].includes(String((item as ChatMessage).role)) &&
      typeof (item as ChatMessage).content === "string",
    ).slice(-40);
  } catch {
    return NextResponse.json({ error: "요청 형식이 올바르지 않습니다." }, { status: 400 });
  }

  try {
    const upstream = await fetch(endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}) },
      body: JSON.stringify({ model: "aura", messages, stream: false }),
      cache: "no-store",
      signal: AbortSignal.timeout(90_000),
    });
    const payload = await upstream.json().catch(() => null);
    if (!upstream.ok) {
      return NextResponse.json({ error: payload?.error?.message || payload?.detail || "모델 서버에서 오류가 발생했습니다." }, { status: upstream.status });
    }
    const content = payload?.choices?.[0]?.message?.content ?? payload?.message ?? payload?.response;
    if (typeof content !== "string" || !content.trim()) {
      return NextResponse.json({ error: "모델 서버 응답에 답변 텍스트가 없습니다." }, { status: 502 });
    }
    return NextResponse.json({ content });
  } catch (error) {
    const message = error instanceof Error && error.name === "TimeoutError" ? "모델 응답 시간이 초과되었습니다." : "모델 서버에 연결할 수 없습니다.";
    return NextResponse.json({ error: message }, { status: 502 });
  }
}
