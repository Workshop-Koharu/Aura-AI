import { NextResponse,type NextRequest } from "next/server";
import { createClient } from "@/lib/supabase/server";
export async function GET(request:NextRequest){
 const code=request.nextUrl.searchParams.get("code"),next=request.nextUrl.searchParams.get("next")??"/";
 const safe=next.startsWith("/")&&!next.startsWith("//")?next:"/";
 if(code){const supabase=await createClient();const {error}=await supabase.auth.exchangeCodeForSession(code);if(!error)return NextResponse.redirect(new URL(safe,request.url));}
 return NextResponse.redirect(new URL("/login?error=oauth",request.url));
}
