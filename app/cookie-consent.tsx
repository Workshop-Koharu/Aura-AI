"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
type Consent={essential:true;analytics:boolean;preferences:boolean;updatedAt:string};
const KEY="aura-cookie-consent-v1";
export default function CookieConsent(){
 const [open,setOpen]=useState(true),[details,setDetails]=useState(false),[analytics,setAnalytics]=useState(false),[preferences,setPreferences]=useState(true);
 useEffect(()=>{const timer=window.setTimeout(()=>{try{setOpen(!localStorage.getItem(KEY));}catch{setOpen(false);}},0);return()=>window.clearTimeout(timer);},[]);
 function save(all:boolean,a=analytics,p=preferences){const v:Consent={essential:true,analytics:all||a,preferences:all||p,updatedAt:new Date().toISOString()};try{localStorage.setItem(KEY,JSON.stringify(v));window.dispatchEvent(new CustomEvent("aura:consent",{detail:v}));}catch{}setOpen(false);}
 if(!open)return null;
 return <div className="cookie-backdrop" role="dialog" aria-modal="true" aria-labelledby="cookie-title"><section className="cookie-card"><p className="auth-eyebrow">YOUR PRIVACY</p><h2 id="cookie-title">쿠키 및 개인정보 설정</h2><p>Aura는 로그인 세션과 보안에 필요한 쿠키를 사용합니다. 선택 쿠키는 동의한 경우에만 사용합니다. <Link href="/privacy">개인정보 처리방침</Link></p><div className="cookie-row"><div><strong>필수 쿠키</strong><small>로그인·보안·서비스 제공에 필요합니다.</small></div><span className="cookie-required">항상 활성화</span></div><div className="cookie-row"><label><strong>환경설정 쿠키</strong><small>언어와 화면 설정을 기억합니다.</small></label><input type="checkbox" checked={preferences} onChange={e=>setPreferences(e.target.checked)}/></div><div className="cookie-row"><label><strong>분석 쿠키</strong><small>이용 통계와 성능 개선에 사용합니다.</small></label><input type="checkbox" checked={analytics} onChange={e=>setAnalytics(e.target.checked)}/></div>{details&&<p className="cookie-detail">선택은 브라우저에 저장되며 언제든지 변경할 수 있습니다. 분석 도구는 동의 전 실행하지 않습니다.</p>}<button className="cookie-more" onClick={()=>setDetails(!details)}>쿠키 상세 설명</button><div className="cookie-actions"><button className="cookie-secondary" onClick={()=>save(false)}>선택 저장</button><button className="cookie-secondary" onClick={()=>save(false,false,false)}>선택 항목 거부</button><button className="cookie-primary" onClick={()=>save(true)}>모두 동의</button></div></section></div>;
}
