import {NextResponse,type NextRequest} from "next/server";
import {createClient} from "@/lib/supabase/server";
import {notifyLoginIfNew} from "@/lib/auth-email";
export const runtime="nodejs";
export async function POST(request:NextRequest){
 const s=await createClient();const {data:{user},error}=await s.auth.getUser();
 if(error||!user)return NextResponse.json({error:"Unauthorized"},{status:401});
 await notifyLoginIfNew(s,user,request);return NextResponse.json({ok:true});
}
