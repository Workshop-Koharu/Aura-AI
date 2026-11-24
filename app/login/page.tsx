import {Suspense} from "react";import LoginClient from "./login-client";
export const metadata={title:"로그인 · Aura"};
export default function LoginPage(){return <Suspense fallback={<main className="auth-page"/>}><LoginClient/></Suspense>;}
