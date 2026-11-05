const $=s=>document.querySelector(s);
const state={conversations:[],active:null,attachments:[],recording:null,guestTurns:Number(sessionStorage.getItem("aura.guestTurns")||0),loading:false};
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]));
const isLoggedIn=()=>!!window.AuraAuth?.user;
const db=()=>window.AuraAuth?.client;
const userId=()=>window.AuraAuth?.user?.id;
const icon=(name)=>{const paths={
copy:'<rect x="8" y="8" width="12" height="12" rx="2"/><path d="M16 8V5a2 2 0 0 0-2-2H5a2 2 0 0 0-2 2v9a2 2 0 0 0 2 2h3"/>',
trash:'<path d="M3 6h18M8 6V4h8v2m3 0-1 14H6L5 6m4 4v6m6-6v6"/>',
file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6"/>',
settings:'<circle cx="12" cy="12" r="3"/><path d="m19.4 15 .1.1 1.2 2.1-2 2-2.1-1.2-.1-.1a7.8 7.8 0 0 1-1.7.7l-.6 2.4h-2.8l-.6-2.4a7.8 7.8 0 0 1-1.7-.7l-2.2 1.2-2-2 1.2-2.1a7.8 7.8 0 0 1-.7-1.7L3 12.7V9.9l2.4-.6a7.8 7.8 0 0 1 .7-1.7L4.9 5.5l2-2L9 4.7a7.8 7.8 0 0 1 1.7-.7l.6-2.4h2.8l.6 2.4a7.8 7.8 0 0 1 1.7.7l2.1-1.2 2 2-1.2 2.1a7.8 7.8 0 0 1 .7 1.7l2.4.6v2.8l-2.4.6a7.8 7.8 0 0 1-.6 1.7Z'
};return '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'+(paths[name]||'')+'</svg>';};
function active(){return state.conversations.find(c=>c.id===state.active);}
function renderList(){const list=$("#conversationList");if(!list)return;list.innerHTML=state.conversations.map(c=>'<button class="history-item '+(c.id===state.active?"selected":"")+'" data-id="'+esc(c.id)+'">'+esc(c.title||"New chat")+'</button>').join("");list.querySelectorAll("[data-id]").forEach(b=>b.onclick=()=>openConversation(b.dataset.id));}
function renderMessages(){const c=active(),msgs=c?.messages||[];$("#welcome").style.display=msgs.length?"none":"block";$("#messages").innerHTML=msgs.map(m=>'<article class="message '+esc(m.role)+'">'+(m.role==="assistant"?'<div class="message-avatar"><img src="/assets/aura-mark.png" alt="Aura"></div>':'')+'<div class="message-content">'+esc(m.text)+(m.files?.length?'<div class="message-files">'+m.files.map(f=>esc(typeof f==="string"?f:f.name)).join("<br>")+'</div>':'')+(m.role==="assistant"?'<div class="message-actions"><button data-copy="'+encodeURIComponent(m.text)+'">'+icon("copy")+'<span>복사</span></button></div>':'')+'</div></article>').join("");$("#messages").querySelectorAll("[data-copy]").forEach(b=>b.onclick=()=>navigator.clipboard.writeText(decodeURIComponent(b.dataset.copy)));$("#chatScroll").scrollTop=$("#chatScroll").scrollHeight;}
function renderAll(){renderList();renderMessages();}
function setAttachments(){const strip=$("#attachmentStrip");strip.innerHTML=state.attachments.map((f,i)=>'<div class="attachment-chip"><span>'+icon("file")+esc(f.name)+'</span><button data-remove="'+i+'" aria-label="첨부 삭제">'+icon("trash")+'</button></div>').join("");strip.querySelectorAll("[data-remove]").forEach(b=>b.onclick=()=>{state.attachments.splice(+b.dataset.remove,1);setAttachments();});}
function setComposerStatus(text){$("#composerStatus").textContent=text;}
async function dbError(error){console.error("Aura database:",error);setComposerStatus("대화 저장 오류 · 데이터베이스 설정을 확인하세요");}
async function saveConversation(c){if(!isLoggedIn())return true;const {error}=await db().from("aura_conversations").upsert({id:c.id,user_id:userId(),title:c.title||"New chat",model_id:"aura",updated_at:new Date().toISOString()},{onConflict:"id"});if(error){await dbError(error);return false;}return true;}
async function saveMessage(c,m){if(!isLoggedIn())return true;const {error}=await db().from("aura_messages").insert({conversation_id:c.id,user_id:userId(),role:m.role,content:m.text,attachments:(m.files||[]).map(f=>typeof f==="string"?{name:f}:{name:f.name,type:f.type}),usage:{}});if(error){await dbError(error);return false;}return true;}
async function loadSaved(){if(!isLoggedIn()){state.conversations=[];state.active=null;renderAll();return;}if(!db()){setComposerStatus("데이터베이스 연결 중");return;}const {data,error}=await db().from("aura_conversations").select("id,title,updated_at,created_at").order("updated_at",{ascending:false}).limit(100);if(error){await dbError(error);state.conversations=[];state.active=null;renderAll();return;}state.conversations=(data||[]).map(c=>({...c,messages:[]}));state.active=state.conversations[0]?.id||null;renderAll();if(state.active)await loadMessages(state.active);setComposerStatus("대화 기록이 계정에 저장됩니다");}
async function loadMessages(id){const c=state.conversations.find(x=>x.id===id);if(!c)return;const {data,error}=await db().from("aura_messages").select("id,role,content,attachments,created_at").eq("conversation_id",id).order("created_at",{ascending:true}).limit(500);if(error){await dbError(error);return;}c.messages=(data||[]).map(m=>({id:m.id,role:m.role,text:m.content,files:Array.isArray(m.attachments)?m.attachments:[]}));renderAll();}
async function openConversation(id){state.active=id;renderAll();await loadMessages(id);}
async function newChat(){const c={id:crypto.randomUUID(),title:"새 채팅",messages:[],updated_at:new Date().toISOString()};state.conversations.unshift(c);state.active=c.id;if(isLoggedIn()&&!await saveConversation(c)){state.conversations.shift();state.active=state.conversations[0]?.id||null;renderAll();return;}renderAll();$("#messageInput").focus();}
async function deleteHistory(){if(!isLoggedIn())return;if(!confirm("모든 대화 기록을 계정에서 삭제할까요?"))return;const {error}=await db().from("aura_conversations").delete().eq("user_id",userId());if(error){await dbError(error);return;}state.conversations=[];state.active=null;renderAll();}
function applyLanguage(lang){document.documentElement.lang=lang;const en=lang==="en";const set=(selector,value)=>{const el=$(selector);if(el)el.textContent=value;};set("#newChat span",en?"New chat":"새 채팅");set("#navChat span",en?"Chat":"채팅");set(".history-heading span",en?"Recent chats":"최근 대화");set("#settingsTitle",en?"Settings":"설정");set(".settings-section h3",en?"General":"일반");set(".welcome h1",en?"How can I help you today?":"무엇이든 물어보세요");set(".welcome-copy",en?"A global AI service for writing, coding, research, learning, and everyday problem-solving.":"글쓰기, 코딩, 연구, 학습과 일상적인 문제 해결을 지원하는 글로벌 AI 서비스입니다.");$("#messageInput").placeholder=en?"Message Aura AI":"Aura에게 메시지 보내기";set("#settingsAuthAction",isLoggedIn()?(en?"Sign out":"로그아웃"):(en?"Sign in":"로그인"));}
function renderPreferences(){const theme=localStorage.getItem("aura.theme")||"light",lang=localStorage.getItem("aura.language")||"ko";$("#themePreference").value=theme;$("#languagePreference").value=lang;applyLanguage(lang);$("#settingsAccountEmail").textContent=window.AuraAuth?.user?.email||"비로그인 사용자";$("#settingsAuthAction").textContent=isLoggedIn()?(lang==="en"?"Sign out":"로그아웃"):(lang==="en"?"Sign in":"로그인");}
function applyTheme(value){localStorage.setItem("aura.theme",value);const dark=value==="dark"||(value==="system"&&matchMedia("(prefers-color-scheme: dark)").matches);document.documentElement.dataset.theme=dark?"dark":"light";}
function showSettings(){$("#settingsModal").hidden=false;renderPreferences();}
function closeSettings(){$("#settingsModal").hidden=true;}
async function send(){
 const input=$("#messageInput"),message=input.value.trim(),files=state.attachments.slice();
 if((!message&&!files.length)||state.loading)return;
 if(!isLoggedIn()&&state.guestTurns>=5){window.AuraAuth?.show();return;}
 if(!isLoggedIn()&&files.length){window.AuraAuth?.show();return;}
 if(!state.active){if(isLoggedIn())await newChat();else{const c={id:crypto.randomUUID(),title:"New chat",messages:[]};state.conversations=[c];state.active=c.id;}}
 const c=active();if(!c)return;
 const fileNames=files.map(f=>({name:f.name,type:f.type}));
 const userMessage={role:"user",text:message||"첨부 파일 분석 요청",files:fileNames};
 if(isLoggedIn()){
   if(!await saveConversation(c))return;
   if(!await saveMessage(c,userMessage))return;
 }
 c.messages.push(userMessage);if(c.messages.length===1){c.title=(message||files[0]?.name||"New chat").slice(0,48);if(isLoggedIn()&&!await saveConversation(c)){c.messages.pop();return;}}
 state.attachments=[];setAttachments();input.value="";input.style.height="auto";renderAll();
 const placeholder={role:"assistant",text:"응답 생성 중…"};c.messages.push(placeholder);renderMessages();state.loading=true;$("#sendButton").disabled=true;
 try{
  const prior=c.messages.slice(0,-1).slice(-12).map(m=>(m.role==="user"?"User: ":"Assistant: ")+m.text).join("\n");
  const prompt=[prior,message||"Analyze the attached files and summarize their key information."].filter(Boolean).join("\nUser: ").slice(-18000);
  const body={message:prompt,files:files.map(f=>({name:f.name,type:f.type,base64:f.base64}))};
  const res=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}),data=await res.json();
  if(!res.ok)throw new Error(data.detail||data.error||"Request failed.");
  placeholder.text=data.text||"";
  if(!isLoggedIn()){state.guestTurns++;sessionStorage.setItem("aura.guestTurns",String(state.guestTurns));if(state.guestTurns>=5)setTimeout(()=>window.AuraAuth?.show(),450);}
  else if(!await saveMessage(c,placeholder)){placeholder.text="응답은 생성됐지만 대화 기록 저장에 실패했습니다. 다시 시도하기 전에 데이터베이스 설정을 확인하세요.";}
 }catch(e){placeholder.text="요청 오류: "+e.message;}
 finally{state.loading=false;$("#sendButton").disabled=false;renderAll();if(isLoggedIn()){const {error}=await db().from("aura_conversations").update({updated_at:new Date().toISOString()}).eq("id",c.id);if(error)await dbError(error);}}
}
$("#sendButton").onclick=send;
$("#messageInput").addEventListener("input",e=>{e.target.style.height="auto";e.target.style.height=Math.min(e.target.scrollHeight,180)+"px";});
$("#messageInput").addEventListener("keydown",e=>{if(e.key==="Enter"&&!e.shiftKey){e.preventDefault();send();}});
$("#newChat").onclick=()=>{if(isLoggedIn())newChat();else{$("#messageInput").value="";$("#messageInput").focus();}};
$("#clearHistory").onclick=deleteHistory;
$("#attachButton").onclick=()=>{if(!isLoggedIn()){window.AuraAuth?.show();return;}$("#fileInput").click();};
$("#fileInput").onchange=async e=>{if(!isLoggedIn()){window.AuraAuth?.show();e.target.value="";return;}for(const file of e.target.files){if(file.size>3*1024*1024){alert(file.name+": 파일은 3MB 이하만 첨부할 수 있습니다.");continue;}const ext=file.name.split(".").pop().toLowerCase(),allowed=["image/","text/"];if(!allowed.some(t=>file.type.startsWith(t))&&file.type!=="audio/wav"&&file.type!=="audio/x-wav"&&!["pdf","docx","xlsx","pptx","md","json","csv","py","js"].includes(ext)){alert("지원하지 않는 파일 형식: "+file.name);continue;}const base64=await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.readAsDataURL(file);});const total=state.attachments.reduce((n,f)=>n+(f.base64?.length||0),0)+base64.length;if(total>4*1024*1024){alert("첨부 파일 전체 용량은 약 3MB 이하로 제한됩니다.");continue;}state.attachments.push({name:file.name,type:file.type||"application/octet-stream",base64});}setAttachments();e.target.value="";};
document.querySelectorAll(".suggestion").forEach(b=>b.onclick=()=>{$("#messageInput").value=b.dataset.prompt;send();});
$("#openSettings").onclick=showSettings;$("#settingsButton").onclick=showSettings;document.querySelectorAll("[data-close-modal]").forEach(b=>b.onclick=closeSettings);$("#settingsModal").onclick=e=>{if(e.target.id==="settingsModal")closeSettings();};
$("#themePreference").onchange=e=>applyTheme(e.target.value);
$("#languagePreference").onchange=e=>{localStorage.setItem("aura.language",e.target.value);applyLanguage(e.target.value);};
$("#settingsAuthAction").onclick=async()=>{if(isLoggedIn()){await db().auth.signOut();closeSettings();}else{closeSettings();window.AuraAuth?.show();}};
$("#openSidebar").onclick=()=>$("#sidebar").classList.add("open");$("#closeSidebar").onclick=()=>$("#sidebar").classList.remove("open");$("#collapseSidebar").onclick=()=>$("#sidebar").classList.toggle("collapsed");
$("#voiceButton").onclick=async()=>{if(!isLoggedIn()){window.AuraAuth?.show();return;}if(state.recording){state.recording.stop();return;}try{const stream=await navigator.mediaDevices.getUserMedia({audio:true}),recorder=new MediaRecorder(stream),chunks=[];state.recording=recorder;recorder.ondataavailable=e=>chunks.push(e.data);recorder.onstop=async()=>{try{const blob=new Blob(chunks,{type:recorder.mimeType}),ctx=new AudioContext(),decoded=await ctx.decodeAudioData(await blob.arrayBuffer()),channel=decoded.getChannelData(0),buffer=new ArrayBuffer(44+channel.length*2),view=new DataView(buffer),write=(o,s)=>{for(let i=0;i<s.length;i++)view.setUint8(o+i,s.charCodeAt(i));};write(0,"RIFF");view.setUint32(4,36+channel.length*2,true);write(8,"WAVE");write(12,"fmt ");view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,decoded.sampleRate,true);view.setUint32(28,decoded.sampleRate*2,true);view.setUint16(32,2,true);view.setUint16(34,16,true);write(36,"data");view.setUint32(40,channel.length*2,true);for(let i=0;i<channel.length;i++)view.setInt16(44+i*2,Math.max(-1,Math.min(1,channel[i]))*32767,true);const wav=new Blob([buffer],{type:"audio/wav"}),base64=await new Promise(resolve=>{const r=new FileReader();r.onload=()=>resolve(r.result);r.readAsDataURL(wav);});state.attachments.push({name:"voice-recording.wav",type:"audio/wav",base64});setAttachments();await ctx.close();}catch(err){alert("음성 파일 변환 실패: "+err.message);}finally{stream.getTracks().forEach(t=>t.stop());state.recording=null;$("#voiceButton").classList.remove("recording");}};recorder.start();$("#voiceButton").classList.add("recording");}catch(e){alert("마이크 접근 오류: "+e.message);}};
document.addEventListener("keydown",e=>{if((e.ctrlKey||e.metaKey)&&e.key.toLowerCase()==="k"){e.preventDefault();if(isLoggedIn())newChat();else{$("#messageInput").value="";$("#messageInput").focus();}}if(e.key==="Escape")closeSettings();});
window.addEventListener("aura-auth-changed",()=>{loadSaved();renderPreferences();});
applyTheme(localStorage.getItem("aura.theme")||"light");
renderAll();
setComposerStatus("Connecting to Aura AI…");
