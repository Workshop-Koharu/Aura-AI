import {NextResponse,type NextRequest} from "next/server";
import {createClient} from "@/lib/supabase/server";
import {notifyLoginIfNew,sendWelcomeOnce} from "@/lib/auth-email";
export const runtime="nodejs";
export async function GET(request:NextRequest){
 const code=request.nextUrl.searchParams.get("code"),next=request.nextUrl.searchParams.get("next")??"/";
 const safe=next.startsWith("/")&&!next.startsWith("//")?next:"/";
 if(code){const s=await createClient();const {data,error}=await s.auth.exchangeCodeForSession(code);if(!error){if(data.user){await sendWelcomeOnce(s,data.user);await notifyLoginIfNew(s,data.user,request);}return NextResponse.redirect(new URL(safe,request.url));}}
 return NextResponse.redirect(new URL("/login?error=oauth",request.url));
}
