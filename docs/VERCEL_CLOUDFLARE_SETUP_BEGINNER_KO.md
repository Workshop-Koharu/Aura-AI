# Aura AI 배포 설정 완전 초보자 가이드: Vercel + Cloudflare Tunnel

> 목표: 웹사이트는 **https://aura.koharu.live**, API는 **https://api-aura.koharu.live**로 연결한다.
>
> Windows PC 기준으로, 대시보드에서 무엇을 누르고 어떤 값을 입력하는지 단계별로 설명한다. 화면 이름은 서비스 업데이트에 따라 조금씩 달라질 수 있다. 실제 대시보드가 표시하는 DNS 대상, 검증 값, 설치 명령이 이 문서와 다르면 해당 대시보드의 최신 값을 우선한다.

---

## 0. 전체 구조부터 이해하기

Aura AI는 웹 화면과 API 서버로 나뉜다.

- **Vercel**: 방문자가 보는 Next.js 웹사이트를 배포한다.
- **Cloudflare DNS**: aura.koharu.live과 api-aura.koharu.live이라는 이름을 올바른 서비스로 연결한다.
- **Cloudflare Tunnel**: 외부 요청을 실행 중인 Connector를 통해 원본 서버로 전달한다.
- **Render**: 현재 Aura AI API가 실행되는 서버다.

~~~text
방문자 브라우저
    |
    | https://aura.koharu.live
    v
Vercel (Aura AI 웹앱)
    |
    | 브라우저가 API 요청
    | https://api-aura.koharu.live/health
    v
Cloudflare DNS / 프록시
    |
    v
Cloudflare Tunnel
    |
    | 실행 중인 cloudflared Connector
    v
Render API 서비스
    https://aura-ai-api-1gt5.onrender.com
~~~

### 현재 프로젝트 정보

| 항목 | 값 |
|---|---|
| 웹 저장소 | https://github.com/Workshop-Koharu/Aura-AI-Web |
| API/문서 저장소 | https://github.com/Workshop-Koharu/Aura-AI |
| 웹 저장소 배포 브랜치 | main |
| 웹 프로젝트 이름 | aura-ai-web |
| 원하는 웹 도메인 | aura.koharu.live |
| API 공개 도메인 | api-aura.koharu.live |
| 현재 Render API 원본 주소 | https://aura-ai-api-1gt5.onrender.com |
| Cloudflare Tunnel 이름 | aura-ai-api |
| Tunnel ID | e54844e0-97b1-4630-8eb2-af1bf6a3ad18 |

Tunnel ID는 비밀값이 아니다. 하지만 **Tunnel token은 비밀번호처럼 취급**해야 한다. 토큰을 GitHub, 문서, 스크린샷, 공개 로그, 채팅에 붙여 넣지 않는다.

---

# 1부. Vercel 웹앱 설정

## 1. Vercel에 로그인

1. 브라우저에서 https://vercel.com/dashboard 를 연다.
2. Aura AI 프로젝트를 관리하는 계정으로 로그인한다.
3. 대시보드에서 aura-ai-web 프로젝트를 찾는다.
4. 프로젝트가 안 보이면 현재 로그인한 계정이 올바른지 확인한다. 다른 계정에 프로젝트가 있다면 임의로 새 프로젝트를 중복 생성하지 않는다.

## 2. GitHub 저장소 연결 확인

웹앱은 GitHub의 Workshop-Koharu/Aura-AI-Web 저장소에서 가져와야 한다.

1. Vercel 대시보드에서 aura-ai-web을 연다.
2. **Settings** 탭을 누른다.
3. 왼쪽 메뉴에서 **Git**을 연다.
4. Connected Git Repository 항목을 찾는다.
5. 다음 저장소가 연결되어 있는지 확인한다: Workshop-Koharu/Aura-AI-Web.
6. Production Branch가 main인지 확인한다.
7. 저장소가 연결되어 있지 않으면 Connect Git Repository 또는 비슷한 버튼을 누른다.
8. GitHub를 선택하고 저장소 접근 권한을 승인한다.
9. 목록에서 정확한 저장소를 선택한다.

### 저장소 목록에 안 나타날 때

- GitHub에 로그인한 계정이 저장소를 볼 수 있는지 확인한다.
- 조직 저장소라면 Vercel GitHub App이 해당 저장소에 접근하도록 승인해야 할 수 있다.
- 조직 관리자 승인이나 저장소 권한이 필요한 경우 소유자에게 권한을 요청한다.
- 접근할 수 없는 저장소 대신 이름이 비슷한 다른 저장소를 선택하지 않는다.

## 3. 프로젝트를 새로 가져오는 방법

기존 aura-ai-web 프로젝트가 없다면 다음과 같이 한다.

1. Vercel 대시보드에서 **Add New…**를 누른다.
2. **Project**를 선택한다.
3. GitHub 저장소 목록에서 Workshop-Koharu/Aura-AI-Web을 찾는다.
4. **Import**를 누른다.
5. Project Name은 aura-ai-web으로 설정한다.
6. Framework Preset이 자동으로 **Next.js**로 선택되는지 확인한다.
7. Root Directory는 저장소 루트인 ./ 를 사용한다. 웹앱이 하위 폴더에 있는 구조가 아니라면 바꾸지 않는다.
8. Build Command는 기본값을 사용한다. 일반적으로 npm run build다.
9. Output Directory는 Next.js 기본값을 사용한다. 임의로 dist로 바꾸지 않는다.
10. 필요한 환경변수를 설정한 뒤 **Deploy**를 누른다.
11. 배포 화면에서 빌드 로그를 확인한다. 상태가 Ready가 될 때까지 기다린다.

기존 프로젝트가 이미 있다면 중복 프로젝트를 만들지 말고 기존 프로젝트의 Git 연결을 먼저 확인한다.

## 4. API 주소 환경변수 설정

웹앱이 어느 API 서버에 요청을 보낼지 지정해야 한다.

1. Vercel에서 aura-ai-web 프로젝트를 연다.
2. **Settings → Environment Variables**로 이동한다.
3. 다음 변수를 추가한다.

| 입력란 | 입력값 |
|---|---|
| Key | NEXT_PUBLIC_API_BASE_URL |
| Value (초기 직접 연결 테스트용) | https://aura-ai-api-1gt5.onrender.com |
| Environments | Production, Preview, Development 중 필요한 환경 |

처음에는 Render 주소를 넣어서 API 통신부터 확인하는 것이 가장 쉽다. Cloudflare Tunnel Connector가 정상 연결된 뒤에는 Value를 다음 주소로 변경한다.

**https://api-aura.koharu.live**

주의: Next.js의 NEXT_PUBLIC_ 변수는 웹 브라우저에 포함될 수 있다. 이 변수에는 공개 API 주소처럼 비밀이 아닌 값만 넣는다. API 키, 비밀번호, Tunnel 토큰을 절대 넣지 않는다.

환경변수를 바꾼 다음에는 기존 배포에 자동 반영되었다고 가정하지 않는다. **Deployments** 탭에서 새 배포를 실행하거나 새 배포가 시작되었는지 확인한다.

## 5. 웹앱 배포 및 빌드 로그 확인

1. 프로젝트의 **Deployments** 탭을 연다.
2. 최신 배포 항목을 누른다.
3. Build Logs를 연다.
4. 오류가 있으면 가장 먼저 표시된 실제 오류부터 확인한다. 로그 마지막 줄만 보고 원인을 단정하지 않는다.
5. 배포가 성공하면 상태가 **Ready**로 표시되는지 확인한다.
6. Vercel이 제공하는 vercel.app 주소를 연다.
7. Aura AI 첫 화면이 표시되는지 확인한다.

웹앱은 Next.js로 작성되어 있으며, 로컬에서 npm run build는 성공했고 npm run lint도 오류 없이 종료했다. 이 결과는 로컬 빌드·정적 검사 결과이며, Vercel에 실제 배포되었다는 뜻은 아니다.

## 6. Vercel에 사용자 도메인 추가하기

목표는 https://aura.koharu.live 이다.

1. Vercel에서 aura-ai-web 프로젝트를 연다.
2. **Settings → Domains**로 이동한다.
3. **Add Domain** 또는 비슷한 버튼을 누른다.
4. aura.koharu.live을 입력한다.
5. Add를 눌러 추가한다.
6. Vercel이 표시하는 상태와 DNS 안내를 읽는다.

Vercel이 DNS 설정값을 보여주면 화면에 나온 값을 그대로 기록한다. 흔히 CNAME 대상이 표시되지만, 프로젝트나 계정 상태에 따라 별도 값 또는 TXT 검증 레코드가 요구될 수 있다.

**Vercel 화면이 보여주는 최신 DNS 값을 우선한다.** 이 문서의 예시를 맹목적으로 복사하지 않는다.

### 현재 Cloudflare DNS에 입력된 웹 레코드

현재 확인된 초기 설정은 다음과 같다.

- Type: CNAME
- Name: aura
- Target: cname.vercel-dns.com
- Proxy status: DNS only (회색 구름)

이 레코드는 초기 설정값이다. Vercel Domains 화면에서 다른 CNAME 대상이나 TXT 검증 레코드를 표시한다면 Cloudflare DNS에서 Vercel이 요구하는 최신값으로 수정하거나 추가한다.

### 도메인 상태별 의미

- **Valid Configuration / Verified**: Vercel이 DNS 구성을 확인했다.
- **Invalid Configuration**: DNS 대상 또는 검증 레코드가 맞지 않을 수 있다.
- **Pending**: DNS 전파 또는 검증이 진행 중일 수 있다.
- **Certificate Pending**: HTTPS 인증서 발급을 기다리는 상태일 수 있다.

도메인을 추가한 것만으로 완료된 것은 아니다. Vercel이 정상 설정으로 표시하고 실제 HTTPS 주소가 열리는지 확인한다.

## 7. Vercel의 403 권한 오류 해결

이 프로젝트 설정을 자동으로 변경하려 했을 때 Vercel API가 HTTP 403을 반환한 적이 있다. 403은 대체로 현재 인증 계정에 해당 작업 권한이 없다는 뜻이다. DNS 문제와는 다른 종류의 오류다.

1. https://vercel.com/dashboard 에서 현재 로그인 계정을 확인한다.
2. 우측 상단 계정 메뉴에서 올바른 Personal Account 또는 Team을 선택한다.
3. aura-ai-web 프로젝트가 해당 계정/Team 소유인지 확인한다.
4. Settings → General 또는 프로젝트 상단에서 프로젝트 소유 범위를 확인한다.
5. Settings → Git에서 올바른 GitHub 저장소를 연결할 권한이 있는지 확인한다.
6. 도메인을 추가할 때 Team 권한 또는 도메인 관리 권한이 부족하다고 표시되면 소유자/관리자에게 권한을 요청한다.
7. Vercel에 로그인한 계정과 프로젝트 소유 계정이 다르면 올바른 계정으로 전환한다.

권한이 없는 경우 API 요청을 반복하는 것으로 해결되지 않는다. **올바른 계정 또는 소유자의 권한 승인이 필요하다.** 인증 토큰을 문서나 저장소에 올리지 않는다.

## 8. Vercel 확인 체크리스트

- [ ] aura-ai-web 프로젝트가 올바른 계정에 있다.
- [ ] Git 저장소가 Workshop-Koharu/Aura-AI-Web이다.
- [ ] Production Branch가 main이다.
- [ ] 최신 Deployment가 Ready다.
- [ ] NEXT_PUBLIC_API_BASE_URL이 올바르다.
- [ ] Settings → Domains에 aura.koharu.live이 있다.
- [ ] 도메인 상태가 Valid Configuration 또는 Verified다.
- [ ] https://aura.koharu.live 이 HTTPS로 열린다.
- [ ] 웹앱의 API 연결 확인 버튼이 성공한다.

---

# 2부. Cloudflare DNS 설정

## 9. Cloudflare 대시보드 열기

1. https://dash.cloudflare.com/ 에 접속한다.
2. 계정으로 로그인한다.
3. 도메인 목록에서 koharu.live을 선택한다.
4. **DNS → Records**로 이동한다.

Cloudflare 계정의 UI에 따라 DNS 메뉴는 왼쪽 메뉴 또는 도메인 개요 화면에 표시될 수 있다.

## 10. 웹 도메인 DNS 확인

DNS Records에서 aura.koharu.live에 해당하는 레코드를 찾는다.

| 필드 | 값 |
|---|---|
| Type | CNAME |
| Name | aura |
| Target / Content | cname.vercel-dns.com (Vercel이 최신 화면에서 다른 값을 주면 그 값) |
| TTL | Auto |
| Proxy status | DNS only 권장(초기 검증용) |

Cloudflare DNS 레코드의 Name에는 대개 전체 도메인이 아니라 aura처럼 서브도메인 부분만 입력한다. 화면이 자동으로 .koharu.live을 붙여 보여줄 수 있다.

회색 구름은 DNS only, 주황색 구름은 Cloudflare proxy를 뜻한다. Vercel 도메인 검증이 실패하면 우선 Vercel이 요구하는 값과 Proxy 상태를 확인한다. 이 문서만 보고 기존 레코드를 무작정 삭제하지 않는다.

## 11. API 서브도메인 DNS 확인

Tunnel을 사용할 API 주소는 api-aura.koharu.live이다.

| 필드 | 값 |
|---|---|
| Type | CNAME |
| Name | api-aura |
| Target / Content | e54844e0-97b1-4630-8eb2-af1bf6a3ad18.cfargotunnel.com |
| TTL | Auto |
| Proxy status | Proxied (주황색 구름) |

이 레코드는 Cloudflare Tunnel의 공개 호스트 이름을 가리킨다. Connector가 실행되지 않는 상태라면 DNS가 존재해도 API 요청은 실패할 수 있다.

### 기존 API 레코드를 덮어쓰지 말 것

현재 api.koharu.live에는 이미 다른 Tunnel을 가리키는 CNAME이 있다. 기존 서비스에 영향이 생길 수 있으므로 이 가이드에서는 해당 레코드를 변경하지 않고 api-aura.koharu.live을 사용한다.

## 12. DNS 변경사항 저장 및 확인

1. 레코드를 추가하거나 수정한 뒤 Save를 누른다.
2. 목록에서 Type, Name, Target, Proxy 상태가 정확한지 확인한다.
3. 같은 이름으로 중복되거나 충돌하는 CNAME이 없는지 확인한다.
4. Vercel이 TXT 검증 레코드를 요구하면 TXT도 별도로 추가한다.
5. Vercel이 정상 구성이라고 표시하기 전에는 도메인 연결이 완료되었다고 판단하지 않는다.

DNS 변경은 즉시 반영될 수도 있고 캐시/전파 때문에 시간이 걸릴 수도 있다.

---

# 3부. Cloudflare Tunnel 설정

## 13. Tunnel이 무엇인지 쉽게 이해하기

일반적인 서버 연결은 인터넷에서 서버로 직접 들어오는 연결을 허용해야 하는 경우가 많다. Cloudflare Tunnel은 서버 쪽에서 Cloudflare로 나가는 연결을 유지해 외부 요청을 전달할 수 있게 해 준다.

반드시 구분해야 할 것은 세 가지다.

1. **Tunnel 객체**: Cloudflare에 저장된 터널 설정이다.
2. **Public Hostname / Ingress**: 어떤 도메인의 요청을 어떤 원본 주소로 전달할지 정하는 규칙이다.
3. **Connector (cloudflared)**: 실제로 실행 중이며 Tunnel에 연결되는 프로그램이다.

첫 번째와 두 번째가 있어도 세 번째가 없으면 요청이 전달되지 않는다. 현재 Tunnel은 설정을 저장했지만 Connector가 inactive인 상태로 확인됐다. 이 가이드의 가장 중요한 미완료 작업이 Connector를 실행하는 것이다.

## 14. Cloudflare Zero Trust에서 기존 Tunnel 열기

1. https://one.dash.cloudflare.com/ 을 연다.
2. Cloudflare 계정에 로그인한다.
3. 올바른 계정을 선택한다.
4. **Networks → Tunnels** 또는 **Connectors → Cloudflare Tunnels**로 이동한다. UI 버전에 따라 메뉴 이름이 다를 수 있다.
5. Tunnel 목록에서 aura-ai-api를 찾는다.
6. 해당 Tunnel을 연다.
7. Tunnel ID가 다음과 같은지 확인한다: e54844e0-97b1-4630-8eb2-af1bf6a3ad18.
8. 상태가 Healthy / Connected인지 확인한다. 현재까지 확인된 상태는 inactive였다.

Tunnel이 목록에 없다면 다른 계정 또는 Team을 보고 있을 수 있다. 새 Tunnel을 중복 생성하기 전에 계정 선택부터 확인한다.

## 15. Public Hostname 설정 확인

Tunnel의 Public Hostnames, Published application routes 또는 비슷한 탭을 연다.

| 필드 | 값 |
|---|---|
| Hostname | api-aura.koharu.live |
| Service Type | HTTP/HTTPS |
| URL | https://aura-ai-api-1gt5.onrender.com |
| Catch-all | 마지막에 HTTP 404 처리 |

이 규칙은 다음 의미다.

“사용자가 https://api-aura.koharu.live/health에 요청하면 Cloudflare Tunnel이 Render API의 https://aura-ai-api-1gt5.onrender.com/health로 요청을 전달한다.”

원본 서비스 주소는 API가 실제로 실행 중인 Render URL이어야 한다. Vercel 웹앱 URL을 원본 서비스로 넣으면 안 된다.

### 원본 서비스 HTTPS 설정

Render 주소는 HTTPS이므로 원본 서비스도 다음으로 설정한다.

https://aura-ai-api-1gt5.onrender.com

원본 TLS 인증서 검증을 끄는 옵션을 임의로 켜지 않는다. 연결 오류가 발생하면 먼저 Render URL을 직접 열어 인증서와 API 상태를 확인한다.

## 16. Connector 설치 명령 준비

이 단계는 Windows PC를 Connector로 사용할 때의 설명이다. Connector를 계속 켜 둘 수 있는 PC 또는 서버가 필요하다. 개인 PC를 끄거나 절전 모드로 두면 연결이 끊길 수 있다. 장기 운영에서는 상시 실행 가능한 호스트를 사용한다.

1. Zero Trust에서 aura-ai-api Tunnel을 연다.
2. Configure, Install connector, Add a replica 또는 비슷한 항목을 찾는다.
3. 운영체제로 Windows를 선택한다.
4. Cloudflare가 표시하는 설치 안내를 그대로 따른다.
5. Windows용 cloudflared 설치 파일 또는 공식 설치 방법을 사용한다.
6. 대시보드가 제공하는 Connector 실행 명령을 확인한다.

공식 문서: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/

### 토큰을 다루는 규칙

대시보드가 제공하는 Tunnel token은 이 Tunnel에 Connector를 연결하는 비밀 인증정보다.

- 토큰을 GitHub에 올리지 않는다.
- 토큰을 .env.example, README, Markdown 가이드에 적지 않는다.
- 토큰을 화면 캡처에 노출하지 않는다.
- 토큰을 공개 채팅이나 이슈에 붙여 넣지 않는다.
- 토큰이 노출되었다면 Cloudflare에서 회전/재발급 절차를 확인한다.

이 가이드는 실제 토큰 값을 포함하지 않는다.

## 17. Windows에서 cloudflared 설치

Cloudflare가 대시보드에 제공하는 최신 Windows 설치 방법을 우선한다. 설치 프로그램이 제공되는 경우 공식 다운로드를 사용한다.

공식 다운로드/설치 안내:
https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/

설치 후 PowerShell을 연다.

1. 시작 메뉴를 누른다.
2. PowerShell을 검색한다.
3. Windows PowerShell을 연다.
4. 다음 명령을 실행한다.

~~~powershell
cloudflared --version
~~~

버전이 출력되면 설치 확인이 된 것이다. “명령을 찾을 수 없습니다”라고 나오면 설치가 완료되지 않았거나 PATH에 등록되지 않은 것이다. Cloudflare 공식 설치 절차를 다시 확인한 뒤 새 PowerShell 창을 열어 재시도한다.

Dashboard가 Connector 설치를 위해 전용 명령을 제공하면 그 명령을 우선한다. 비밀 토큰을 임의로 만들거나 추측하지 않는다.

## 18. Connector 실행 및 상태 확인

Cloudflare Dashboard가 Windows용으로 제공하는 명령을 그대로 사용한다. 일반적으로 Tunnel token을 이용한 실행 명령이 표시되지만, **실제 토큰이 포함된 명령을 이 문서나 GitHub에 저장하면 안 된다.**

1. Dashboard의 Connector 설치 화면에서 명령을 복사한다.
2. 로컬 PowerShell에서만 실행한다.
3. 명령이 실행되는 동안 PowerShell 창을 닫지 않는다.
4. Cloudflare Zero Trust의 Tunnels 화면으로 돌아간다.
5. 상태가 Healthy 또는 Connected로 바뀌는지 확인한다.
6. Connector 로그에 인증 실패, DNS 실패, 원본 연결 실패가 없는지 확인한다.

테스트가 끝나도 PowerShell을 닫지 않아야 연결이 유지된다. PowerShell을 닫으면 해당 프로세스가 종료되어 Tunnel이 다시 비활성화될 수 있다.

## 19. Windows 서비스로 실행하기

일반 PowerShell 창에서 Connector를 실행하는 방법은 테스트에 적합하지만, 운영 환경에서는 Windows 재시작 후에도 Connector가 자동으로 시작되도록 서비스 방식으로 설치하는 편이 낫다.

1. Cloudflare의 공식 Windows 서비스 설치 절차를 확인한다.
2. Dashboard가 안내하는 서비스 설치 명령을 사용한다.
3. 관리자 권한이 필요한 경우에만 관리자 PowerShell을 연다.
4. 설치 후 Windows Services 관리 도구에서 Cloudflare Tunnel/cloudflared 서비스 상태를 확인한다.
5. Startup Type이 자동 시작으로 설정되었는지 확인한다.
6. PC를 재시작한 뒤 Connector가 다시 연결되는지 확인한다.

공식 문서:
https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/configure-tunnels/local-management/as-a-service/windows/

토큰을 명령 기록이나 공개 로그에 남기지 않도록 주의한다. 실제 설치 명령과 옵션은 Cloudflare가 제공하는 최신 공식 안내를 따른다. 토큰을 평문으로 저장하는 방식이 보안 정책상 적합하지 않다면 운영 환경의 보안 저장 방식을 사용한다.

## 20. Connector 연결 후 API 테스트

먼저 Render 원본이 살아 있는지 확인한다.

https://aura-ai-api-1gt5.onrender.com/health

정상 응답:

~~~json
{"status":"ok"}
~~~

그다음 Tunnel 도메인을 테스트한다.

https://api-aura.koharu.live/health

정상적으로 연결되었다면 동일하게 다음 JSON이 나와야 한다.

~~~json
{"status":"ok"}
~~~

PowerShell에서 테스트하려면 다음을 실행한다.

~~~powershell
Invoke-RestMethod "https://aura-ai-api-1gt5.onrender.com/health"
Invoke-RestMethod "https://api-aura.koharu.live/health"
~~~

정상인 경우 각 명령에서 status : ok가 출력된다.

---

# 4부. CORS와 웹앱-API 연결

## 21. CORS를 쉽게 이해하기

브라우저는 보안상 한 웹사이트가 다른 출처(origin)의 API를 호출할 때 서버가 허용했는지 확인한다.

이번 프로젝트에서 웹앱과 API는 서로 다른 도메인이다.

- 웹: https://aura.koharu.live
- API: https://api-aura.koharu.live

따라서 API 서버가 웹 도메인을 CORS 허용 목록에 포함해야 한다.

Render의 API 환경변수에서 다음을 확인한다.

| Key | Value |
|---|---|
| AURA_ENVIRONMENT | production |
| AURA_CORS_ORIGINS | https://aura.koharu.live |

환경변수 이름은 코드와 정확히 일치해야 한다. 주소 끝에 임의로 / 를 추가하지 않는다.

## 22. Render에서 환경변수 확인하기

1. https://dashboard.render.com/ 을 연다.
2. 올바른 workspace를 선택한다.
3. aura-ai-api 서비스를 연다.
4. **Environment** 메뉴를 연다.
5. AURA_ENVIRONMENT 값이 production인지 확인한다.
6. AURA_CORS_ORIGINS 값이 https://aura.koharu.live인지 확인한다.
7. 값이 변경되면 Save Changes를 누른다.
8. Render가 재배포를 시작하면 완료될 때까지 기다린다.
9. Deploys/Logs에서 서비스가 정상 실행 중인지 확인한다.

CORS는 Tunnel 자체를 고치는 설정이 아니다. Tunnel 요청은 되는데 브라우저에서만 CORS 오류가 난다면 이 설정을 확인한다.

## 23. Vercel 환경변수를 Tunnel 주소로 전환

Connector가 정상 연결되고 다음 테스트가 성공한 뒤에만 진행한다.

https://api-aura.koharu.live/health

그다음 Vercel에서:

1. aura-ai-web 프로젝트를 연다.
2. Settings → Environment Variables를 연다.
3. NEXT_PUBLIC_API_BASE_URL을 찾는다.
4. Value를 https://api-aura.koharu.live 로 변경한다.
5. Production 환경에 적용한다.
6. 저장한다.
7. Deployments에서 새 배포를 실행한다.
8. 최신 배포가 Ready가 될 때까지 기다린다.

Tunnel 테스트가 아직 실패한다면 우선 직접 Render 주소를 사용해 웹앱과 API가 통신하는지 확인할 수 있다. 다만 Render 주소로 직접 호출하는 경우 Cloudflare Tunnel 경로를 테스트한 것은 아니다.

---

# 5부. 전체 통합 테스트

## 24. 테스트를 실행할 순서

반드시 아래 순서대로 확인한다. 앞 단계가 실패하면 뒤 단계에서 원인을 찾기 어렵다.

### 테스트 A: Render 원본 API

브라우저에서 연다.

https://aura-ai-api-1gt5.onrender.com/health

기대 결과:

~~~json
{"status":"ok"}
~~~

실패하면 Render의 Deploys와 Logs를 확인한다.

### 테스트 B: Cloudflare Tunnel

브라우저에서 연다.

https://api-aura.koharu.live/health

기대 결과:

~~~json
{"status":"ok"}
~~~

실패하면 아래 오류 해결표를 본다.

### 테스트 C: Vercel 기본 도메인

Vercel Deployments에서 제공하는 vercel.app URL을 연다.

- 화면이 뜨는가?
- CSS가 적용되었는가?
- 브라우저 콘솔에 오류가 있는가?
- API 연결 확인 버튼이 작동하는가?

### 테스트 D: 사용자 도메인

https://aura.koharu.live

- HTTPS 인증서 오류 없이 열리는가?
- Vercel의 Aura AI 웹 화면이 표시되는가?
- API 연결 확인 버튼이 성공하는가?

### 테스트 E: 브라우저 개발자 도구

1. 웹사이트에서 F12를 누른다.
2. **Console** 탭을 연다.
3. 빨간색 오류가 있는지 확인한다.
4. **Network** 탭을 연다.
5. API 연결 확인 버튼을 누른다.
6. health 요청을 선택한다.
7. Request URL이 https://api-aura.koharu.live/health인지 확인한다.
8. HTTP Status가 200인지 확인한다.
9. Response에 {"status":"ok"}가 나오는지 확인한다.

---

# 6부. 자주 나오는 오류와 해결 방법

## 25. Vercel 빌드 실패

**증상:** Deployment 상태가 Error다.

1. 해당 배포를 열고 Build Logs를 본다.
2. 최초의 실제 오류를 찾는다.
3. Framework Preset이 Next.js인지 확인한다.
4. Root Directory가 웹앱 저장소의 루트인지 확인한다.
5. Build Command가 npm run build인지 확인한다.
6. 필요한 환경변수가 있는지 확인한다.
7. 코드를 수정했다면 GitHub의 main에 올린 뒤 새 배포를 확인한다.

## 26. Vercel 도메인 설정이 Invalid

**증상:** aura.koharu.live에 Invalid Configuration이 표시된다.

1. Vercel Settings → Domains에서 필요한 DNS 레코드를 읽는다.
2. Cloudflare DNS → Records로 이동한다.
3. aura CNAME의 Target을 비교한다.
4. Vercel이 TXT 레코드를 요구하면 해당 TXT를 추가한다.
5. 잘못된 중복 레코드가 있는지 확인한다.
6. Vercel의 최신 DNS 안내와 일치시킨다.
7. 다시 검증한다.

기존에 사용 중인 다른 도메인 레코드를 확인 없이 삭제하지 않는다.

## 27. Cloudflare 오류 1033

**뜻:** Cloudflare가 Tunnel을 통해 요청을 전달할 수 있는 연결된 Connector를 찾지 못하는 경우에 나타난다.

이 프로젝트에서는 Connector가 inactive였기 때문에 특히 먼저 확인해야 할 오류다.

해결 순서:

1. Zero Trust → Networks/Tunnels에서 aura-ai-api를 연다.
2. Connector 상태를 확인한다.
3. Connector가 꺼져 있다면 Windows 설치 및 실행 절차를 진행한다.
4. 인증 토큰이 올바른 Tunnel의 것인지 확인한다.
5. 실행 로그에서 연결 오류를 확인한다.
6. 상태가 Healthy/Connected가 된 뒤 API 도메인을 다시 테스트한다.

DNS CNAME을 반복해서 바꾸는 것만으로는 Connector 비활성 문제가 해결되지 않는다.

## 28. API 주소에서 502 또는 5xx 오류

1. 먼저 Render URL을 직접 연다.
2. Render 원본이 정상이라면 Tunnel의 원본 Service URL이 정확한지 확인한다.
3. Service URL은 https://aura-ai-api-1gt5.onrender.com 이어야 한다.
4. Connector 로그에서 원본 TLS/연결 오류를 확인한다.
5. Render 서비스 로그에서 API 프로세스가 실행 중인지 확인한다.

## 29. 웹사이트는 뜨지만 API 연결 버튼이 실패함

순서대로 확인한다.

1. 브라우저에서 API /health 주소가 열리는가?
2. Vercel의 NEXT_PUBLIC_API_BASE_URL 값이 맞는가?
3. 환경변수 변경 뒤 새 배포를 했는가?
4. Render의 AURA_CORS_ORIGINS가 정확한 웹 도메인인가?
5. 브라우저 Console에 CORS 오류가 있는가?
6. Network 탭에서 API 요청 URL과 HTTP 상태 코드를 확인한다.

CORS 오류와 DNS/Tunnel 오류는 서로 다른 문제다. Console/Network 메시지를 보고 구분한다.

## 30. PowerShell에서 cloudflared 명령을 찾을 수 없음

1. 설치가 완료됐는지 확인한다.
2. 공식 Cloudflare 설치 페이지에서 Windows 설치 안내를 확인한다.
3. 새 PowerShell 창을 연다.
4. cloudflared --version을 다시 실행한다.
5. 계속 실패하면 설치 경로와 PATH 설정을 확인한다.

## 31. Tunnel이 PC 재부팅 뒤 다시 끊김

테스트용 PowerShell 프로세스는 창을 닫거나 컴퓨터가 재부팅되면 종료될 수 있다.

1. Cloudflare 공식 Windows 서비스 설치 절차를 따른다.
2. 서비스가 자동 시작하도록 설정되었는지 확인한다.
3. Windows Services에서 서비스 상태를 확인한다.
4. 재부팅 후 Cloudflare 대시보드에서 Connector가 다시 Connected/Healthy인지 확인한다.

---

# 7부. 보안 체크리스트

## 32. 절대 GitHub에 올리면 안 되는 것

- Cloudflare Tunnel token
- API 키
- 비밀번호
- 개인 액세스 토큰
- 인증서 개인 키
- 실제 운영 환경변수 파일 .env
- 서비스 계정의 비밀 JSON 파일

GitHub에는 .env.example처럼 변수 이름과 안전한 예시만 올린다. 실제 비밀값은 Vercel/Render/Cloudflare의 비밀 설정 영역에만 입력한다.

## 33. 공개 도메인과 내부 주소

- aura.koharu.live: 공개 웹 도메인
- api-aura.koharu.live: 공개 API 도메인
- aura-ai-api-1gt5.onrender.com: Render API 원본 주소

Tunnel을 사용하는 목적은 공개 API 요청을 Cloudflare Tunnel을 통해 원본으로 전달하는 것이다. DNS 레코드만 존재한다고 Tunnel이 동작하는 것은 아니다.

---

# 8부. 최종 완료 확인표

아래 항목을 모두 완료하면 기본 웹앱과 API 연결이 완료된 것이다.

## Vercel

- [ ] 올바른 Vercel 계정/Team 선택
- [ ] aura-ai-web 프로젝트 확인
- [ ] GitHub의 Workshop-Koharu/Aura-AI-Web 연결
- [ ] Production Branch main
- [ ] 최신 배포 Ready
- [ ] NEXT_PUBLIC_API_BASE_URL 설정
- [ ] aura.koharu.live 도메인 추가
- [ ] Vercel이 요구하는 DNS 값으로 Cloudflare 레코드 검증
- [ ] HTTPS 웹 도메인 접속 성공

## Cloudflare DNS

- [ ] aura CNAME이 Vercel의 최신 안내와 일치
- [ ] 필요한 TXT 검증 레코드 추가
- [ ] api-aura CNAME이 Tunnel 주소를 가리킴
- [ ] API CNAME은 Proxied 상태
- [ ] 기존 api.koharu.live 레코드를 무단 변경하지 않음

## Cloudflare Tunnel

- [ ] 기존 aura-ai-api Tunnel 선택
- [ ] Public Hostname api-aura.koharu.live 설정
- [ ] 원본 서비스 https://aura-ai-api-1gt5.onrender.com
- [ ] Connector 설치
- [ ] Connector 상태 Healthy/Connected
- [ ] 재부팅 후에도 Connector 자동 시작
- [ ] https://api-aura.koharu.live/health 에서 JSON 응답 성공

## Render 및 통합 테스트

- [ ] Render 서비스 정상 실행
- [ ] AURA_ENVIRONMENT=production
- [ ] AURA_CORS_ORIGINS=https://aura.koharu.live
- [ ] 웹앱 환경변수가 올바른 API 도메인을 가리킴
- [ ] 환경변수 변경 후 웹앱 재배포
- [ ] 웹앱에서 API 연결 확인 성공
- [ ] 브라우저 Console에 해결되지 않은 오류가 없음

---

# 9부. 공식 문서 링크

- Vercel Dashboard: https://vercel.com/dashboard
- Vercel Git 배포: https://vercel.com/docs/deployments/git
- Vercel 도메인 설정: https://vercel.com/docs/domains/working-with-domains/add-a-domain
- Vercel 환경변수: https://vercel.com/docs/environment-variables
- Cloudflare Dashboard: https://dash.cloudflare.com/
- Cloudflare Zero Trust: https://one.dash.cloudflare.com/
- Cloudflare Tunnel 시작하기: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/
- Cloudflare Tunnel 다운로드: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/
- Cloudflare Tunnel Windows 서비스: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/configure-tunnels/local-management/as-a-service/windows/
- Cloudflare DNS 레코드: https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-dns-records/
- Render Dashboard: https://dashboard.render.com/

---

## 지금 가장 먼저 할 일

현재 상황에서 가장 효율적인 순서는 다음과 같다.

1. **Cloudflare Tunnel Connector를 실행**해 aura-ai-api 상태를 Healthy/Connected로 만든다.
2. https://api-aura.koharu.live/health 에서 {"status":"ok"}가 나오는지 확인한다.
3. Vercel에서 aura-ai-web의 Git 연결과 권한을 확인한다.
4. Vercel Settings → Domains에 aura.koharu.live을 추가하고 화면에 표시되는 최신 DNS 값을 Cloudflare에 반영한다.
5. Vercel 환경변수 NEXT_PUBLIC_API_BASE_URL=https://api-aura.koharu.live 을 설정하고 재배포한다.
6. https://aura.koharu.live 을 열어 API 연결 확인 버튼까지 성공하는지 테스트한다.

위 6단계를 마치기 전에는 전체 배포가 완료되었다고 판단하지 않는다.
