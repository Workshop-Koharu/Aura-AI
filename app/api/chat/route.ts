import {NextRequest,NextResponse} from "next/server";
import {createClient} from "@/lib/supabase/server";
export const runtime="nodejs";
export const dynamic="force-dynamic";
export const maxDuration=60;
type Msg={role:"user"|"assistant";content:string};
export async function POST(request:NextRequest){
 const s=await createClient();const {data:{user},error:authError}=await s.auth.getUser();
 if(authError||!user)return NextResponse.json({error:"로그인이 필요합니다."},{status:401,headers:{"Cache-Control":"no-store"}});
 let body:{messages?:Msg[];conversationId?:string};try{body=await request.json();}catch{return NextResponse.json({error:"요청 형식이 올바르지 않습니다."},{status:400});}
 if(!Array.isArray(body.messages)||!body.messages.length)return NextResponse.json({error:"메시지가 비어 있습니다."},{status:400});
 const messages=body.messages.filter((m):m is Msg=>!!m&&["user","assistant"].includes(String(m.role))&&typeof m.content==="string"&&m.content.length>0).slice(-24);
 if(!messages.length||messages.at(-1)?.role!=="user")return NextResponse.json({error:"마지막 메시지는 사용자 입력이어야 합니다."},{status:400});
 if(messages.some(m=>m.content.length>16000))return NextResponse.json({error:"메시지가 너무 깁니다."},{status:413});
 let conversationId=body.conversationId;
 if(conversationId){const {data,error}=await s.from("conversations").select("id").eq("id",conversationId).eq("user_id",user.id).maybeSingle();if(error||!data)return NextResponse.json({error:"대화를 찾을 수 없습니다."},{status:404});}
 else{const title=messages.filter(m=>m.role==="user").at(-1)?.content.slice(0,80)??"새 대화";const {data,error}=await s.from("conversations").insert({user_id:user.id,title}).select("id").single();if(error||!data)return NextResponse.json({error:"대화를 저장하지 못했습니다."},{status:500});conversationId=data.id;}
 const latest=messages.at(-1)!;const {error:saveError}=await s.from("messages").insert({conversation_id:conversationId,user_id:user.id,role:"user",content:latest.content});if(saveError)return NextResponse.json({error:"메시지를 저장하지 못했습니다."},{status:500});
 const endpoint=(process.env.AURA_MODEL_API_URL||process.env.AURA_INFERENCE_URL||"").replace(/\/+$/,""),key=process.env.AURA_MODEL_API_KEY||process.env.AURA_GATEWAY_SECRET;
 if(!endpoint)return NextResponse.json({error:"모델 추론 서버가 아직 연결되지 않았습니다.",conversationId},{status:503});
 try{
  const url=endpoint.endsWith("/chat/completions")?endpoint:endpoint+"/v1/chat/completions";
  const upstream=await fetch(url,{method:"POST",headers:{"Content-Type":"application/json",...(key?{Authorization:"Bearer "+key}:{})},body:JSON.stringify({model:"aura",messages,stream:false,max_tokens:512,temperature:0.7}),cache:"no-store",signal:AbortSignal.timeout(55000)});
  const payload=await upstream.json().catch(()=>null);if(!upstream.ok)return NextResponse.json({error:payload?.error?.message||payload?.detail||`모델 서버 오류 (${upstream.status})`,conversationId},{status:502,headers:{"Cache-Control":"no-store"}});
  const content=payload?.choices?.[0]?.message?.content??payload?.message??payload?.response;if(typeof content!=="string"||!content.trim())return NextResponse.json({error:"모델 응답에 텍스트가 없습니다.",conversationId},{status:502});
  const {error:assistantError}=await s.from("messages").insert({conversation_id:conversationId,user_id:user.id,role:"assistant",content});if(assistantError)return NextResponse.json({error:"답변 저장에 실패했습니다.",conversationId},{status:500});
  await s.from("conversations").update({updated_at:new Date().toISOString()}).eq("id",conversationId).eq("user_id",user.id);
  return NextResponse.json({content,conversationId},{headers:{"Cache-Control":"no-store"}});
 }catch(e){const msg=e instanceof Error&&e.name==="TimeoutError"?"모델 응답 시간이 초과되었습니다.":"모델 서버에 연결할 수 없습니다.";return NextResponse.json({error:msg,conversationId},{status:502,headers:{"Cache-Control":"no-store"}});}
}
