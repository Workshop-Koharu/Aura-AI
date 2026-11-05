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

function renderMarkdown(value){
 let x=esc(value||"");
 x=x.replace(/^### (.+)$/gm,"<h3>$1</h3>").replace(/^## (.+)$/gm,"<h2>$1</h2>").replace(/^# (.+)$/gm,"<h1>$1</h1>");
 x=x.replace(/\*\*(.+?)\*\*/g,"<strong>$1</strong>").replace(/\*(.+?)\*/g,"<em>$1</em>");
 x=x.replace(/^[-*] (.+)$/gm,"<li>$1</li>").replace(/(<li>.*<\/li>)/g,"<ul>$1</ul>");
 x=x.replace(/\n/g,"<br>");
 return x;
}

function renderMessages(){const c=active(),msgs=c?.messages||[];$("#welcome").style.display=msgs.length?"none":"block";$("#messages").innerHTML=msgs.map(m=>'<article class="message '+esc(m.role)+'">'+(m.role==="assistant"?'<div class="message-avatar"><img src="/assets/aura-mark.png" alt="Aura"></div>':'')+'<div class="message-content">'+(m.role==="assistant"?renderMarkdown(m.text):esc(m.text).replace(/\n/g,"<br>"))+(m.files?.length?'<div class="message-files">'+m.files.map(f=>esc(typeof f==="string"?f:f.name)).join("<br>")+'</div>':'')+(m.role==="assistant"&&m.sources?.length?'<details class="source-panel"><summary>출처 · '+m.sources.length+'</summary><ol>'+m.sources.map((x,i)=>'<li><a href="'+esc(x.url)+'" target="_blank" rel="noopener noreferrer">['+(i+1)+'] '+esc(x.title)+'</a><p>'+esc(x.snippet||"")+'</p></li>').join("")+'</ol><small>'+esc(m.search_date||"")+'</small></details>':"")+(m.role==="assistant"?'<div class="message-actions"><button data-copy="'+encodeURIComponent(m.text)+'">'+icon("copy")+'<span>복사</span></button></div>':'')+'</div></article>').join("");$("#messages").querySelectorAll("[data-copy]").forEach(b=>b.onclick=()=>navigator.clipboard.writeText(decodeURIComponent(b.dataset.copy)));$("#chatScroll").scrollTop=$("#chatScroll").scrollHeight;}
function renderAll(){renderList();renderMessages();}
function setAttachments(){const strip=$("#attachmentStrip");strip.innerHTML=state.attachments.map((f,i)=>'<div class="attachment-chip"><span>'+icon("file")+esc(f.name)+'</span><button data-remove="'+i+'" aria-label="첨부 삭제">'+icon("trash")+'</button></div>').join("");strip.querySelectorAll("[data-remove]").forEach(b=>b.onclick=()=>{state.attachments.splice(+b.dataset.remove,1);setAttachments();});}
function setComposerStatus(text){$("#composerStatus").textContent=text;}
async function dbError(error){console.error("Aura database:",error);setComposerStatus("대화 저장 오류 · 데이터베이스 설정을 확인하세요");}
async function saveConversation(c){if(!isLoggedIn())return true;const {error}=await db().from("aura_conversations").upsert({id:c.id,user_id:userId(),title:c.title||"New chat",model_id:"aura",updated_at:new Date().toISOString()},{onConflict:"id"});if(error){await dbError(error);return false;}return true;}
async function saveMessage(c,m){if(!isLoggedIn())return true;const {error}=await db().from("aura_messages").insert({conversation_id:c.id,user_id:userId(),role:m.role,content:m.text,attachments:(m.files||[]).map(f=>typeof f==="string"?{name:f}:{name:f.name,type:f.type}),usage:{sources:m.sources||[],search_date:m.search_date||null}});if(error){await dbError(error);return false;}return true;}
async function loadSaved(){if(!isLoggedIn()){state.conversations=[];state.active=null;renderAll();return;}if(!db()){setComposerStatus("데이터베이스 연결 중");return;}const {data,error}=await db().from("aura_conversations").select("id,title,updated_at,created_at").order("updated_at",{ascending:false}).limit(100);if(error){await dbError(error);state.conversations=[];state.active=null;renderAll();return;}state.conversations=(data||[]).map(c=>({...c,messages:[]}));state.active=state.conversations[0]?.id||null;renderAll();if(state.active)await loadMessages(state.active);setComposerStatus("대화 기록이 계정에 저장됩니다");}
async function loadMessages(id){const c=state.conversations.find(x=>x.id===id);if(!c)return;const {data,error}=await db().from("aura_messages").select("id,role,content,attachments,usage,created_at").eq("conversation_id",id).order("created_at",{ascending:true}).limit(500);if(error){await dbError(error);return;}c.messages=(data||[]).map(m=>({id:m.id,role:m.role,text:m.content,files:Array.isArray(m.attachments)?m.attachments:[],sources:m.usage?.sources||[],search_date:m.usage?.search_date||null}));renderAll();}
async function openConversation(id){state.active=id;renderAll();await loadMessages(id);}
async function newChat(){const c={id:crypto.randomUUID(),title:"새 채팅",messages:[],updated_at:new Date().toISOString()};state.conversations.unshift(c);state.active=c.id;if(isLoggedIn()&&!await saveConversation(c)){state.conversations.shift();state.active=state.conversations[0]?.id||null;renderAll();return;}renderAll();$("#messageInput").focus();}
async function deleteHistory(){if(!isLoggedIn())return;if(!confirm("모든 대화 기록을 계정에서 삭제할까요?"))return;const {error}=await db().from("aura_conversations").delete().eq("user_id",userId());if(error){await dbError(error);return;}state.conversations=[];state.active=null;renderAll();}
function applyLanguage(lang){
 document.documentElement.lang=lang;
 const dict={
 ko:{newChat:"새 채팅",chat:"채팅",recent:"최근 대화",settings:"설정",welcome:"무엇이든 물어보세요",copy:"복사",placeholder:"Aura에게 메시지 보내기",signIn:"로그인",signOut:"로그아웃",sections:["일반","AI 개인화","프로필","개발자","API 키","계정 관리","개인정보 및 지원"],save:"저장",delete:"계정 및 데이터 영구 삭제",profile:"표시 이름",ai:"AI 별명",sources:"출처"},
 en:{newChat:"New chat",chat:"Chat",recent:"Recent chats",settings:"Settings",welcome:"How can I help you today?",copy:"Copy",placeholder:"Message Aura AI",signIn:"Sign in",signOut:"Sign out",sections:["General","AI personalization","Profile","Developer","API keys","Account management","Privacy and support"],save:"Save",delete:"Permanently delete account and data",profile:"Display name",ai:"AI nickname",sources:"Sources"},
 ja:{newChat:"新しいチャット",chat:"チャット",recent:"最近の会話",settings:"設定",welcome:"今日はどのようにお手伝いできますか？",copy:"コピー",placeholder:"Aura AI にメッセージを送信",signIn:"ログイン",signOut:"ログアウト",sections:["一般","AI パーソナライズ","プロフィール","開発者","API キー","アカウント管理","プライバシーとサポート"],save:"保存",delete:"アカウントとデータを完全に削除",profile:"表示名",ai:"AI のニックネーム",sources:"出典"}
 };
 const x=dict[lang]||dict.en, set=(q,v)=>{const e=$(q);if(e)e.textContent=v;};
 set("#newChat span",x.newChat);set("#navChat span",x.chat);set(".history-heading span",x.recent);set("#settingsTitle",x.settings);set(".welcome h1",x.welcome);
 $("#messageInput").placeholder=x.placeholder;
 document.querySelectorAll(".settings-section h3").forEach((e,i)=>{if(x.sections[i])e.textContent=x.sections[i];});
 set("#saveAiPreferences",x.save);set("#saveProfileSettings",x.save);set("#deleteAccountButton",x.delete);
 const rowCopy={
 ko:[["언어","인터페이스 표시 언어"],["테마","화면 표시 방식"],["AI 별명","응답에서 사용할 AI 이름"],["AI 인격","대화 성격과 말투"],["응답 길이","답변의 기본 상세도"],["웹 검색","최신 정보 검색 사용"],["출처 표시","검색 근거를 답변 아래에 표시"],["표시 이름","계정에 표시할 이름"],["로그인 계정","현재 로그인된 계정"]],
 en:[["Language","Interface language"],["Theme","Appearance"],["AI nickname","Name used by the assistant"],["AI persona","Conversation personality and tone"],["Response length","Default answer detail"],["Web search","Search for current information"],["Show sources","Display references below answers"],["Display name","Name shown on your account"],["Signed-in account","Currently signed-in account"]],
 ja:[["言語","画面の表示言語"],["テーマ","画面の外観"],["AI のニックネーム","AI が使用する名前"],["AI の性格","会話の性格と口調"],["回答の長さ","回答の詳しさ"],["ウェブ検索","最新情報を検索"],["出典を表示","回答の下に参照元を表示"],["表示名","アカウントに表示する名前"],["ログイン中のアカウント","現在ログインしているアカウント"]]
 }[lang]||[];
 document.querySelectorAll(".settings-section .preference-row").forEach((row,i)=>{if(!rowCopy[i])return;const strong=row.querySelector("strong"),small=row.querySelector("small");if(strong)strong.textContent=rowCopy[i][0];if(small)small.textContent=rowCopy[i][1];});
 const options={
 en:{theme:["Light","Dark","System"],persona:["Balanced expert","Friendly and natural","Concise and precise","Creative","Step-by-step teacher"],length:["Concise","Balanced","Detailed"]},
 ja:{theme:["ライト","ダーク","システム"],persona:["バランスの取れた専門家","親しみやすく自然","簡潔で正確","創造的","段階的に教える"],length:["簡潔","標準","詳細"]},
 ko:{theme:["라이트","다크","시스템 설정"],persona:["균형 잡힌 전문가","친근하고 자연스럽게","간결하고 정확하게","창의적이고 자유롭게","단계별로 가르치는 선생님"],length:["간결하게","보통","자세하게"]}
 }[lang]||null;
 if(options){["#themePreference","#aiPersona","#responseLength"].forEach((selector,i)=>{const el=$(selector),values=[options.theme,options.persona,options.length][i];if(el)el.querySelectorAll("option").forEach((o,j)=>{if(values[j])o.textContent=values[j];});});}
 set("#createApiKey",lang==="en"?"Create API key":lang==="ja"?"API キーを発行":"새 API 키 발급");
 $("#apiKeyName").placeholder=lang==="en"?"Key name":lang==="ja"?"キー名":"키 이름";
 $("#profileDisplayName").placeholder=x.profile;$("#aiNickname").placeholder=x.ai;
 set("#settingsAuthAction",isLoggedIn()?x.signOut:x.signIn);window.dispatchEvent(new CustomEvent("aura-language-changed",{detail:{lang}}));
 document.querySelectorAll(".message-actions button span").forEach(e=>e.textContent=x.copy);
}

function renderPreferences(){
 const theme=localStorage.getItem("aura.theme")||"light",lang=localStorage.getItem("aura.language")||"ko";
 $("#themePreference").value=theme;$("#languagePreference").value=lang;applyLanguage(lang);
 $("#settingsAccountEmail").textContent=window.AuraAuth?.user?.email||"비로그인 사용자";
 const prefs=window.AuraAuth?.user?.user_metadata?.aura_preferences||JSON.parse(localStorage.getItem("aura.preferences")||"{}");
 $("#aiNickname").value=prefs.aiNickname||"Aura";$("#aiPersona").value=prefs.aiPersona||"balanced";
 $("#responseLength").value=prefs.responseLength||"balanced";$("#webSearchPreference").checked=prefs.webSearch!==false;
 $("#citationPreference").checked=prefs.citations!==false;$("#profileDisplayName").value=window.AuraAuth?.user?.user_metadata?.display_name||window.AuraAuth?.user?.user_metadata?.full_name||"";
 $("#settingsAuthAction").textContent=isLoggedIn()?(lang==="en"?"Sign out":lang==="ja"?"ログアウト":"로그아웃"):(lang==="en"?"Sign in":lang==="ja"?"ログイン":"로그인");
}
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
  const prefs=JSON.parse(localStorage.getItem("aura.preferences")||"{}");
  const persona={balanced:"Respond as a balanced, capable expert.",friendly:"Use a friendly, natural conversational tone.",precise:"Be concise, precise, and structured.",creative:"Be imaginative while remaining accurate.",teacher:"Teach step by step with clear examples."}[prefs.aiPersona||"balanced"];
  const length={concise:"Keep the answer concise.",balanced:"Use a balanced level of detail.",detailed:"Give a detailed, well-structured answer."}[prefs.responseLength||"balanced"];
  const nickname=prefs.aiNickname||"Aura";
  const systemPrompt="You are "+nickname+", an AI assistant. "+persona+" "+length+" Reply in the user's language. Use structured Markdown when useful.";
  const body={message:systemPrompt+"\\n\\n"+prompt,web_search:prefs.webSearch!==false,client_date:new Intl.DateTimeFormat("en-CA").format(new Date()),files:files.map(f=>({name:f.name,type:f.type,base64:f.base64}))};
  const res=await fetch("/api/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(body)}),data=await res.json();
  if(!res.ok)throw new Error(data.detail||data.error||"Request failed.");
  placeholder.text=data.text||"";placeholder.sources=data.sources||[];placeholder.search_date=data.search_date||null;placeholder.sources=data.sources||[];placeholder.search_date=data.search_date||null;
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
applyLanguage(localStorage.getItem("aura.language")||"ko");
renderAll();
setComposerStatus("Connecting to Aura AI…");

function saveAuraPreferences(){
 const prefs={aiNickname:$("#aiNickname").value.trim()||"Aura",aiPersona:$("#aiPersona").value,responseLength:$("#responseLength").value,webSearch:$("#webSearchPreference").checked,citations:$("#citationPreference").checked};
 localStorage.setItem("aura.preferences",JSON.stringify(prefs));
}
["aiNickname","aiPersona","responseLength","webSearchPreference","citationPreference"].forEach(id=>$("#"+id)?.addEventListener("change",saveAuraPreferences));
$("#saveAiPreferences")?.addEventListener("click",async()=>{
 saveAuraPreferences();
 if(isLoggedIn()){
  const prefs=JSON.parse(localStorage.getItem("aura.preferences")||"{}");
  const {error}=await db().auth.updateUser({data:{aura_preferences:prefs}});
  if(error){alert("개인화 설정 저장 실패: "+error.message);return;}
 }
 alert("개인화 설정을 저장했습니다.");
});
$("#saveProfileSettings")?.addEventListener("click",async()=>{
 if(!isLoggedIn()){window.AuraAuth?.show();return;}
 const name=$("#profileDisplayName").value.trim();
 const {error}=await db().auth.updateUser({data:{display_name:name}});
 if(error){alert("프로필 저장 실패: "+error.message);return;}
 $("#sidebarAccountName").textContent=name||window.AuraAuth.user.email;
 alert("프로필을 저장했습니다.");
});
$("#deleteAccountButton")?.addEventListener("click",async()=>{
 if(!isLoggedIn()){alert("로그인이 필요합니다.");return;}
 const lang=localStorage.getItem("aura.language")||"ko";
 const confirmText=lang==="en"?"Permanently delete your account and all associated data?":lang==="ja"?"アカウントと関連データを完全に削除しますか？":"계정과 모든 관련 데이터를 영구 삭제할까요?";
 if(!confirm(confirmText))return;
 const response=await fetch("/api/account/delete",{method:"DELETE"});
 const result=await response.json().catch(()=>({}));
 if(!response.ok){alert("계정 삭제 실패: "+(result.error||"요청을 처리하지 못했습니다."));return;}
 await db().auth.signOut();location.reload();
});

async function loadApiKeys(){
 const host=$("#apiKeyList");if(!host)return;
 if(!isLoggedIn()){host.textContent="로그인 후 API 키를 관리할 수 있습니다.";return;}
 const {data,error}=await db().from("aura_api_keys").select("id,name,created_at,revoked_at").is("revoked_at",null).order("created_at",{ascending:false});
 if(error){host.textContent="API 키 목록을 불러오지 못했습니다.";return;}
 host.innerHTML=(data||[]).map(k=>'<div class="api-key-row"><span><strong>'+esc(k.name)+'</strong><small>'+new Date(k.created_at).toLocaleString()+'</small></span><button class="secondary-button" data-revoke-key="'+esc(k.id)+'">폐기</button></div>').join("")||'<p class="settings-help">발급된 API 키가 없습니다.</p>';
 host.querySelectorAll("[data-revoke-key]").forEach(button=>button.onclick=async()=>{if(!confirm("이 API 키를 폐기할까요?"))return;const {error}=await db().from("aura_api_keys").update({revoked_at:new Date().toISOString()}).eq("id",button.dataset.revokeKey);if(error){alert("API 키 폐기 실패: "+error.message);return;}loadApiKeys();});
}
$("#createApiKey")?.addEventListener("click",async()=>{
 if(!isLoggedIn()){window.AuraAuth?.show();return;}
 const name=$("#apiKeyName").value.trim()||"Aura API Key";
 const bytes=crypto.getRandomValues(new Uint8Array(32));
 const token="aura_live_"+Array.from(bytes,b=>b.toString(16).padStart(2,"0")).join("");
 const digest=await crypto.subtle.digest("SHA-256",new TextEncoder().encode(token));
 const hash=Array.from(new Uint8Array(digest),b=>b.toString(16).padStart(2,"0")).join("");
 const {error}=await db().from("aura_api_keys").insert({user_id:userId(),name,key_hash:hash});
 if(error){alert("API 키 발급 실패: "+error.message);return;}
 const reveal=$("#apiKeyReveal");reveal.hidden=false;reveal.innerHTML='<strong>새 API 키 · 지금 복사하세요</strong><code>'+esc(token)+'</code><button class="secondary-button" id="copyNewApiKey">복사</button>';
 $("#copyNewApiKey").onclick=()=>navigator.clipboard.writeText(token);
 $("#apiKeyName").value="";loadApiKeys();
});
const previousShowSettings=showSettings;
showSettings=function(){previousShowSettings();loadApiKeys();};
$("#openSettings").onclick=showSettings;$("#settingsButton").onclick=showSettings;
