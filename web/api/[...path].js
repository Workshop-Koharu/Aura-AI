const { Readable } = require("node:stream");
module.exports = async function handler(req, res) {
 const route=(req.url||"/api/health").split("?")[0];
 if(route==="/api/public-config"){res.setHeader("Cache-Control","no-store");return res.status(200).json({supabase_url:process.env.SUPABASE_URL||"",supabase_publishable_key:process.env.SUPABASE_PUBLISHABLE_KEY||"",api_base_url:""});}
 if(route==="/api/health")return res.status(200).json({ok:true,service:"aura-web-gateway"});
 const base=process.env.AURA_INFERENCE_URL,authorization=req.headers.authorization||"";
 const guestAllowed=(req.method==="POST"&&route==="/api/chat")||(req.method==="GET"&&(route==="/api/model/status"||route==="/api/training/status"));
 if(!authorization.startsWith("Bearer ")&&!guestAllowed)return res.status(401).json({error:"Sign-in required for this feature."});
 if(authorization.startsWith("Bearer ")){
  const supabaseUrl=process.env.SUPABASE_URL,publishableKey=process.env.SUPABASE_PUBLISHABLE_KEY;
  if(!supabaseUrl||!publishableKey)return res.status(503).json({error:"Authentication service is not configured."});
  try{
   const identity=await fetch(new URL("/auth/v1/user",supabaseUrl),{headers:{apikey:publishableKey,Authorization:authorization}});
   if(!identity.ok)return res.status(401).json({error:"Session is invalid or expired."});
  }catch(error){return res.status(502).json({error:"Authentication service is unavailable.",detail:error.message});}
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
