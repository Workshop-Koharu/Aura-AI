const { Readable } = require("node:stream");
const { createHash } = require("node:crypto");
module.exports = async function handler(req, res) {
 const route=(req.url||"/api/health").split("?")[0];
 if(route==="/api/public-config"){res.setHeader("Cache-Control","no-store");return res.status(200).json({supabase_url:process.env.SUPABASE_URL||"",supabase_publishable_key:process.env.SUPABASE_PUBLISHABLE_KEY||"",api_base_url:""});}
 if(route==="/api/health")return res.status(200).json({ok:true,service:"aura-web-gateway"});
 const base=process.env.AURA_INFERENCE_URL,authorization=req.headers.authorization||"";
 const guestAllowed=(req.method==="POST"&&route==="/api/chat")||(req.method==="GET"&&route==="/api/model/status");
 if(!authorization.startsWith("Bearer ")&&!guestAllowed)return res.status(401).json({error:"Sign-in required for this feature."});
 if(authorization.startsWith("Bearer ")){
  const supabaseUrl=process.env.SUPABASE_URL,publishableKey=process.env.SUPABASE_PUBLISHABLE_KEY;
  if(!supabaseUrl||!publishableKey)return res.status(503).json({error:"Authentication service is not configured."});
  try{
   const identity=await fetch(new URL("/auth/v1/user",supabaseUrl),{headers:{apikey:publishableKey,Authorization:authorization}});
   if(!identity.ok){
    const raw=authorization.slice(7),serviceKey=process.env.SUPABASE_SERVICE_ROLE_KEY;
    if(!raw.startsWith("aura_live_")||!serviceKey)return res.status(401).json({error:"Session or API key is invalid."});
    const hash=createHash("sha256").update(raw).digest("hex");
    const lookup=new URL("/rest/v1/aura_api_keys",supabaseUrl);
    lookup.searchParams.set("key_hash","eq."+hash);lookup.searchParams.set("revoked_at","is.null");lookup.searchParams.set("select","id,user_id");
    const keyResult=await fetch(lookup,{headers:{apikey:serviceKey,Authorization:"Bearer "+serviceKey}});
    const keys=keyResult.ok?await keyResult.json():[];
    if(!keys.length)return res.status(401).json({error:"Session or API key is invalid."});
    fetch(new URL("/rest/v1/aura_api_keys?id=eq."+keys[0].id,supabaseUrl),{method:"PATCH",headers:{apikey:serviceKey,Authorization:"Bearer "+serviceKey,"Content-Type":"application/json","Prefer":"return=minimal"},body:JSON.stringify({last_used_at:new Date().toISOString()})}).catch(()=>{});
   }
  }catch(error){return res.status(502).json({error:"Authentication service is unavailable."});}
 }

 if(req.method==="DELETE"&&route==="/api/account/delete"){
  const adminKey=process.env.SUPABASE_SERVICE_ROLE_KEY;
  if(!adminKey)return res.status(503).json({error:"Account deletion is not configured."});
  try{
   const supabaseUrl=process.env.SUPABASE_URL,publishableKey=process.env.SUPABASE_PUBLISHABLE_KEY;
   const identity=await fetch(new URL("/auth/v1/user",supabaseUrl),{headers:{apikey:publishableKey,Authorization:authorization}});
   if(!identity.ok)return res.status(401).json({error:"Session is invalid."});
   const user=await identity.json();
   const deleted=await fetch(new URL("/auth/v1/admin/users/"+encodeURIComponent(user.id),supabaseUrl),{method:"DELETE",headers:{apikey:adminKey,Authorization:"Bearer "+adminKey}});
   if(!deleted.ok)return res.status(502).json({error:"Account deletion failed."});
   return res.status(200).json({deleted:true});
  }catch(error){return res.status(502).json({error:"Account deletion failed."});}
 }
 if(!base)return res.status(503).json({error:"Inference endpoint is not configured."});
 try{
  const query=req.url.includes("?")?req.url.slice(req.url.indexOf("?")):"";
  const target=new URL(route+query,base),headers=new Headers();
  for(const name of ["content-type","accept"])if(req.headers[name])headers.set(name,req.headers[name]);
  if(authorization)headers.set("Authorization",authorization);
  if(process.env.AURA_GATEWAY_SECRET)headers.set("X-Aura-Gateway-Key",process.env.AURA_GATEWAY_SECRET);
  const method=req.method||"GET";
  const body=["GET","HEAD"].includes(method)?undefined:await new Promise((resolve,reject)=>{const chunks=[];req.on("data",c=>chunks.push(c));req.on("end",()=>resolve(Buffer.concat(chunks)));req.on("error",reject);});
  const upstream=await fetch(target,{method,headers,body});
  res.statusCode=upstream.status;
  upstream.headers.forEach((v,k)=>{if(!["transfer-encoding","connection","content-encoding"].includes(k.toLowerCase()))res.setHeader(k,v);});
  if(!upstream.body)return res.end();
  Readable.fromWeb(upstream.body).pipe(res);
 }catch(error){return res.status(502).json({error:"Inference service is unavailable.",detail:error.message});}
};
module.exports.config={api:{bodyParser:false}};
