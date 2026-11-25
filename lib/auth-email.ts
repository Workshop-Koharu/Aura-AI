import { createHash } from "node:crypto";
import type { SupabaseClient, User } from "@supabase/supabase-js";
const FROM = "Aura AI <admin@koharu.live>";
const APP_URL = process.env.NEXT_PUBLIC_APP_URL || "https://aura.koharu.live";
function esc(s:string){return s.replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]!));}
export async function sendAuraEmail(to:string,subject:string,html:string){
 const key=process.env.RESEND_API_KEY;if(!key)return {ok:false,error:"RESEND_API_KEY missing"};
 const r=await fetch("https://api.resend.com/emails",{method:"POST",headers:{Authorization:`Bearer ${key}`,"Content-Type":"application/json"},body:JSON.stringify({from:FROM,to:[to],subject,html}),cache:"no-store",signal:AbortSignal.timeout(12000)});
 return r.ok?{ok:true}:{ok:false,error:`Resend HTTP ${r.status}`};
}
// Welcome mail is only eligible immediately after account creation. A persistent
// primary-key claim makes the send idempotent across duplicate OAuth callbacks.
export async function sendWelcomeOnce(s:SupabaseClient,u:User){
 if(!u.email)return;
 const created=Date.parse(u.created_at||"");
 if(!Number.isFinite(created)||Date.now()-created>24*60*60*1000||created>Date.now()+60_000)return;
 const {data,error}=await s.from("auth_welcome_notifications").insert({user_id:u.id}).select("user_id").maybeSingle();
 if(error||!data)return;
 await sendAuraEmail(u.email,"Aura AI에 오신 것을 환영합니다",`<div style="font-family:Arial;max-width:560px;margin:32px auto;padding:32px;color:#20202a;border:1px solid #e7e5ee;border-radius:16px"><h1>Aura AI에 오신 것을 환영합니다</h1><p>${esc(u.email)} 계정의 가입이 완료되었습니다.</p><p><a href="${APP_URL}/chat">Aura AI 시작하기</a></p><p>KCS - Koharu Coding Server</p></div>`);
}
export async function notifyLoginIfNew(s:SupabaseClient,u:User,request:Request){
 if(!u.email)return;
 const ua=request.headers.get("user-agent")||"Unknown device",lang=request.headers.get("accept-language")||"unknown";
 const ip=(request.headers.get("x-vercel-forwarded-for")||request.headers.get("x-forwarded-for")||request.headers.get("x-real-ip")||"").split(",")[0].trim();
 const hash=createHash("sha256").update(`${ua}|${lang}|${ip}`).digest("hex");
 const {data,error}=await s.from("auth_login_events").upsert({user_id:u.id,fingerprint_hash:hash,ip_address:ip||null,user_agent:ua.slice(0,500)},{onConflict:"user_id,fingerprint_hash",ignoreDuplicates:true}).select("id");
 if(error||!data?.length)return;
 const time=new Intl.DateTimeFormat("ko-KR",{dateStyle:"full",timeStyle:"long",timeZone:"Asia/Seoul"}).format(new Date());
 await sendAuraEmail(u.email,"새로운 기기에서 Aura AI 로그인",`<div style="font-family:Arial;max-width:560px;margin:32px auto;padding:32px;color:#20202a;border:1px solid #e7e5ee;border-radius:16px"><h1>새로운 로그인 알림</h1><p>${esc(u.email)} 계정이 새로운 기기 또는 네트워크에서 로그인했습니다.</p><p>시간: ${esc(time)}</p><p>IP 주소: ${esc(ip||"확인할 수 없음")}</p><p>기기: ${esc(ua.slice(0,300))}</p><p>본인이 아니라면 계정 보안을 확인하세요.</p><p>KCS - Koharu Coding Server · admin@koharu.live</p></div>`);
}
