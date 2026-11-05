document.body.insertAdjacentHTML("beforeend",'<div class="auth-gate" id="authGate" hidden><section class="auth-card"><img class="auth-logo" src="/assets/aura-mark.png" alt="Aura"><h1 id="authTitle">Aura에 로그인</h1><p>Sign in to sync your conversations across devices and use file attachments.</p><div class="auth-field"><label for="authEmail">이메일</label><input id="authEmail" type="email" autocomplete="email" placeholder="name@example.com"></div><div class="auth-field" id="authPasswordField"><label for="authPassword">비밀번호</label><input id="authPassword" type="password" autocomplete="current-password" placeholder="8자 이상"></div><input type="hidden" id="authMode" value="login"><button class="auth-submit" id="authSubmit">로그인</button><div class="auth-divider">또는</div><button class="auth-google" id="authGoogle"><svg class="google-mark" viewBox="0 0 48 48" aria-hidden="true"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5Z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.74 7.18l7.72 6C44.42 38.03 46.98 31.92 46.98 24.55Z"/><path fill="#FBBC05" d="M10.53 28.59A14.4 14.4 0 0 1 9.75 24c0-1.59.27-3.13.76-4.59l-7.98-6.2A23.9 23.9 0 0 0 0 24c0 3.87.93 7.53 2.56 10.78l7.97-6.19Z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.91-5.8l-7.72-6c-2.14 1.44-4.89 2.3-8.19 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48Z"/></svg><span>Google 계정으로 계속하기</span></button><div class="auth-links"><button id="authSwitch">계정이 없나요? 회원가입</button><button id="authForgot">비밀번호 찾기</button></div><p class="auth-status" id="authStatus">인증 연결을 확인하고 있습니다.</p><p class="auth-note">Guest conversations are not saved. Sign in to sync chat history and attach files.</p><div class="auth-legal"><a href="/privacy">개인정보 처리방침</a><a href="/terms">서비스 이용약관</a></div><button class="auth-continue" id="authContinue">로그인 없이 계속 사용</button></section></div>');
const $auth=s=>document.querySelector(s);
const authState={client:null,session:null,user:null,showGate:false};
function renderAuraAuth(){
 const user=authState.user;
 $auth("#authGate").hidden=!!user||!authState.showGate;
 document.body.classList.remove("auth-required");
 $auth("#accountLabel").textContent=user?(user.user_metadata?.full_name||user.email):"로그인";
 $auth("#accountAvatar").innerHTML=user?(user.email||"A").slice(0,1).toUpperCase():'<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"><path d="M20 7v5h-5"/><path d="M19 12a7 7 0 1 1-2-5l3 5"/></svg>';
 $auth("#sidebarAccountName").textContent=user?(user.user_metadata?.full_name||user.email):"비로그인 사용자";
 document.querySelector(".history-heading").hidden=!user;
 document.querySelector("#conversationList").hidden=!user;
 document.querySelector("#clearHistory").hidden=!user;
 document.querySelector(".profile small").textContent=user?"Aura AI 계정":"기록 저장 안 함";
 document.querySelector(".composer-foot span:first-child").textContent=user?"대화 기록은 계정에 안전하게 저장됩니다.":"비로그인 모드 · 기록 미저장 · 파일 첨부 불가";
 document.querySelector("#attachButton").disabled=!user;
 document.querySelector("#fileInput").disabled=!user;
 document.querySelector("#voiceButton").disabled=!user;
}
function showAuraLogin(){authState.showGate=true;authMode("login");renderAuraAuth();}
function authMode(mode){
 $auth("#authMode").value=mode;
 $auth("#authTitle").textContent=mode==="signup"?"계정 만들기":mode==="reset"?"비밀번호 재설정":"Aura에 로그인";
 $auth("#authSubmit").textContent=mode==="signup"?"회원가입":mode==="reset"?"재설정 이메일 보내기":"로그인";
 $auth("#authPasswordField").hidden=mode==="reset";
 $auth("#authSwitch").textContent=mode==="signup"?"이미 계정이 있나요? 로그인":mode==="reset"?"로그인으로 돌아가기":"계정이 없나요? 회원가입";
 $auth("#authForgot").hidden=mode!=="login";
}
$auth("#authContinue").onclick=()=>{authState.showGate=false;renderAuraAuth();};
$auth("#authSwitch").onclick=()=>authMode($auth("#authMode").value==="login"?"signup":"login");
$auth("#authForgot").onclick=()=>authMode("reset");
$auth("#authSubmit").onclick=async()=>{
 const c=authState.client;if(!c){$auth("#authStatus").textContent="인증 설정이 완료되지 않았습니다.";return;}
 const mode=$auth("#authMode").value,email=$auth("#authEmail").value.trim(),password=$auth("#authPassword").value;
 if(!email){$auth("#authStatus").textContent="이메일을 입력하세요.";return;}
 if(mode!=="reset"&&password.length<8){$auth("#authStatus").textContent="비밀번호는 8자 이상 입력하세요.";return;}
 $auth("#authSubmit").disabled=true;
 try{
  let r;
  if(mode==="signup")r=await c.auth.signUp({email,password,options:{emailRedirectTo:location.origin+"/"}});
  else if(mode==="reset")r=await c.auth.resetPasswordForEmail(email,{redirectTo:location.origin+"/"});
  else r=await c.auth.signInWithPassword({email,password});
  if(r.error)throw r.error;
  $auth("#authStatus").textContent=mode==="signup"?"인증 이메일을 확인하세요.":mode==="reset"?"비밀번호 재설정 이메일을 보냈습니다.":"로그인 완료";
  if(r.data?.session){authState.session=r.data.session;authState.user=r.data.session.user;authState.showGate=false;renderAuraAuth();window.dispatchEvent(new CustomEvent("aura-auth-changed",{detail:{user:authState.user}}));}
 }catch(e){$auth("#authStatus").textContent=e.message;}
 finally{$auth("#authSubmit").disabled=false;}
};
$auth("#authGoogle").onclick=async()=>{
 if(!authState.client){$auth("#authStatus").textContent="인증 설정이 완료되지 않았습니다.";return;}
 $auth("#authGoogle").disabled=true;
 const {error}=await authState.client.auth.signInWithOAuth({provider:"google",options:{redirectTo:location.origin+"/",queryParams:{prompt:"select_account"}}});
 if(error){$auth("#authStatus").textContent=error.message;$auth("#authGoogle").disabled=false;}
};
$auth("#accountButton").onclick=async()=>{
 if(authState.user){if(confirm("로그아웃할까요?"))await authState.client.auth.signOut();}
 else showAuraLogin();
};
async function initAuraAuth(){
 const cfg=await fetch("/api/public-config",{cache:"no-store"}).then(r=>r.json()).catch(()=>({}));
 if(!cfg.supabase_url||!cfg.supabase_publishable_key){$auth("#authStatus").textContent="인증 설정이 완료되지 않았습니다. 비로그인으로 계속 사용할 수 있습니다.";renderAuraAuth();return;}
 const {createClient}=await import("https://esm.sh/@supabase/supabase-js@2");
 authState.client=createClient(cfg.supabase_url,cfg.supabase_publishable_key,{auth:{persistSession:true,autoRefreshToken:true,detectSessionInUrl:true,flowType:"pkce"}});
 const {data,error}=await authState.client.auth.getSession();if(error)throw error;
 authState.session=data.session;authState.user=data.session?.user||null;
 const originalFetch=window.fetch.bind(window);
 window.fetch=async(input,init={})=>{
  const url=typeof input==="string"?input:input.url;
  if(url.startsWith("/api/")&&!["/api/public-config","/api/health"].includes(url.split("?")[0])){
   const {data}=await authState.client.auth.getSession();
   const headers=new Headers(init.headers||(input instanceof Request?input.headers:undefined));
   if(data.session?.access_token)headers.set("Authorization","Bearer "+data.session.access_token);
   init={...init,headers};
  }
  return originalFetch(input,init);
 };
 renderAuraAuth();
 window.dispatchEvent(new CustomEvent("aura-auth-changed",{detail:{user:authState.user}}));
 authState.client.auth.onAuthStateChange((_event,session)=>{
  authState.session=session;authState.user=session?.user||null;authState.showGate=false;renderAuraAuth();
  window.dispatchEvent(new CustomEvent("aura-auth-changed",{detail:{user:authState.user}}));
 });
}
window.AuraAuth={get user(){return authState.user;},get client(){return authState.client;},show:showAuraLogin,refresh:renderAuraAuth};
authMode("login");renderAuraAuth();initAuraAuth().catch(e=>$auth("#authStatus").textContent="인증 초기화 실패: "+e.message);
