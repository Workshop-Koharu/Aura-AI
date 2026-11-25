import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

export async function POST() {
  const supabase = await createClient();
  const { data: { user }, error: authError } = await supabase.auth.getUser();
  if (authError || !user) {
    return NextResponse.json({ error: "로그인이 필요합니다." }, { status: 401 });
  }
  const { data, error } = await supabase
    .from("conversations")
    .insert({ user_id: user.id, title: "새 대화" })
    .select("id")
    .single();
  if (error || !data) {
    console.error("[Aura conversations] create failed", error?.message ?? "empty result");
    return NextResponse.json({ error: "새 대화를 만들지 못했습니다." }, { status: 500 });
  }
  return NextResponse.json({ conversationId: data.id }, {
    headers: { "Cache-Control": "no-store, max-age=0" },
  });
}
