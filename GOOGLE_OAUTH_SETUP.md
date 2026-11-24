# Google OAuth production setup for Aura

현재 Supabase Auth의 external.google 값은 false입니다. 이 설정이 켜지지 않으면 브라우저 코드가 정상이어도 Unsupported provider가 발생합니다.

## 1. Google Cloud Console
Google Auth Platform → Clients → 기존 Web application OAuth client를 선택합니다.

Authorized JavaScript origins:
- https://aura.koharu.live
- http://localhost:3000 (로컬 테스트용, 선택)

Authorized redirect URIs:
- https://jlfcajlrecnwycplvutp.supabase.co/auth/v1/callback

주의: Google의 Authorized redirect URI는 Supabase Auth callback입니다. Aura의 /auth/callback 경로를 Google redirect URI로 등록하지 않습니다.

## 2. Supabase Dashboard
Authentication → Sign In / Providers → Google
1. Enable Sign in with Google을 ON으로 변경합니다.
2. 기존 Web Client ID를 Client IDs에 입력합니다.
3. Google Client Secret을 Client Secret에 입력합니다.
4. Save 합니다.

Authentication → URL Configuration
- Site URL: https://aura.koharu.live
- Additional Redirect URLs:
  - https://aura.koharu.live/auth/callback
  - https://aura.koharu.live/**
  - http://localhost:3000/auth/callback
  - http://localhost:3000/**

Google OAuth consent screen:
- Homepage: https://aura.koharu.live
- Privacy: https://aura.koharu.live/privacy
- Terms: https://aura.koharu.live/terms
- Authorized domain: koharu.live

## 3. Aura의 브라우저 코드
이 코드는 이미 app/login/login-client.tsx에 적용되어 있습니다. Client Secret은 브라우저에 넣지 않습니다.

```tsx
const { error } = await supabase.auth.signInWithOAuth({
  provider: "google",
  options: {
    redirectTo: window.location.origin +
      "/auth/callback?next=" + encodeURIComponent(nextPath),
    queryParams: { prompt: "select_account" },
  },
});
if (error) setNotice(error.message);
```

app/auth/callback/route.ts가 authorization code를 Supabase session으로 교환한 다음 Aura 내부의 허용된 상대 경로로 이동합니다.

## 4. 설정 확인
다음 주소의 JSON에서 external.google이 true인지 확인합니다:
https://jlfcajlrecnwycplvutp.supabase.co/auth/v1/settings

```json
{ "external": { "google": true } }
```

false라면 Supabase Dashboard에서 Google provider가 아직 활성화/저장되지 않은 것입니다.

## 5. 값의 공개 범위
- Client ID: 공개 식별자입니다.
- Client Secret: Supabase Auth provider 설정에만 저장합니다. NEXT_PUBLIC 변수, 브라우저 코드, Git에 넣지 않습니다.
- Supabase publishable key: RLS가 적용된 브라우저 클라이언트에서 사용 가능합니다.
- PostgreSQL connection URL: 서버/DB 연결 전용이며 사이트 주소나 OAuth redirect 주소로 사용하지 않습니다.