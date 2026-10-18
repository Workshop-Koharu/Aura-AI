# Aura AI 배포·테스트 초보자용 완전 가이드

> 목표: GitHub(main) → Render(FastAPI API) → Cloudflare Tunnel(외부 연결) → Vercel(웹앱) 순서로 연결한다.
>
> 이 문서는 클릭 위치와 명령어를 처음 접하는 사람 기준으로 설명한다. 비밀번호, API 토큰, Tunnel 토큰을 채팅·GitHub·스크린샷에 공개하지 않는다.

## 0. 현재 상태와 먼저 알아둘 점

- 로컬 작업 폴더: `C:\\Users\\L\\Downloads\\Koharu\\Aura-AI`
- AI 저장소로 전달받은 주소: https://github.com/Workshop-Koharu/Aura-AI
- 웹앱 저장소로 전달받은 주소: https://github.com/Workshop-Koharu/Aura-AI-Web
- Vercel 프로젝트 `aura-ai-web`은 생성되어 있다. 웹 저장소 `Workshop-Koharu/Aura-AI-Web`의 Next.js 기초 화면은 `main`에 커밋되었다. Vercel API 변경은 연결 권한 오류(403)로 막혀 Git 연결·배포·프로젝트 도메인 등록은 아직 미완료다.
- Render 서비스 `aura-ai-api`는 생성 및 배포 완료 상태다: https://aura-ai-api-1gt5.onrender.com. `GET /health`에서 `{"status":"ok"}` 응답을 확인했다.
- Cloudflare Tunnel `aura-ai-api` ID `e54844e0-97b1-4630-8eb2-af1bf6a3ad18`을 만들고 원격 설정에 `api-aura.koharu.live` → `https://aura-ai-api-1gt5.onrender.com` 경로를 저장했다. DNS CNAME도 `api-aura.koharu.live` → `e54844e0-97b1-4630-8eb2-af1bf6a3ad18.cfargotunnel.com`으로 추가했지만, connector는 아직 `inactive`라 Tunnel을 통한 요청은 Cloudflare 오류 1033을 반환한다.
- `api.koharu.live`에는 기존 CNAME이 다른 Tunnel을 가리키고 있어 이를 덮어쓰지 않았다. 새 API hostname으로 `api-aura.koharu.live`를 선택했다.
- `aura.koharu.live`에는 CNAME `cname.vercel-dns.com` (DNS only, proxied=false)을 추가했다. 단, Vercel 프로젝트에 도메인을 등록/검증하지 못해 아직 최종 연결 완료를 의미하지 않는다. Vercel 대시보드에서 도메인 추가 후 표시되는 DNS 지시값과 이 레코드가 일치하는지 반드시 확인한다.
- 2026-10-18 API 로컬 검사: `ruff check .` 통과, `pytest -q` 결과 `2 passed`. 웹 빌드는 컴파일은 통과했으나 로컬 npm 설치/타입 검사 과정이 아직 최종 종료되지 않았다.

## 1. 배포 구조를 이해하기

브라우저에서 웹앱을 연다 → Vercel이 웹 화면을 제공한다 → 웹앱이 HTTPS로 API를 호출한다 → 필요하면 Cloudflare Tunnel이 공개 도메인의 요청을 Render API로 전달한다 → FastAPI가 요청을 처리한다.

중요: Tunnel은 AI 모델 자체가 아니다. 외부에서 API 서버로 들어오는 연결을 안전하게 전달하는 통로다. Render는 Python API를 실행하는 곳이다. Vercel은 웹 화면을 호스팅한다. GitHub는 소스 코드와 변경 이력을 보관한다.

처음에는 Render의 공개 HTTPS 주소로 API를 테스트할 수 있다. Cloudflare Tunnel을 반드시 사용해야 한다면, Render 공개 주소를 Tunnel의 origin으로 쓰는 구조는 가능하나 중복 프록시가 되며 보안·DNS 설계를 확인해야 한다. 더 흔한 목적은 사설 네트워크에 있는 서비스에 터널을 연결하는 것이다. 배포 구조를 단순하게 유지하려면 먼저 Render API를 검증한 다음 Tunnel 사용 목적과 DNS를 확정한다.

## 2. 사전 준비

다음 계정에 로그인할 수 있어야 한다.

1. GitHub: 저장소 소유권 또는 쓰기 권한.
2. Vercel: 프로젝트 `aura-ai-web`이 보이는 계정.
3. Render: Aura AI용 워크스페이스.
4. Cloudflare: Tunnel을 생성할 계정. 사용자 지정 도메인을 사용한다면 해당 도메인의 DNS 관리 권한도 필요하다.

Windows에 설치할 프로그램:

- Python 3.11 이상
- Git for Windows
- (선택) VS Code
- (선택, Tunnel을 직접 실행할 PC/서버에서만) cloudflared

설치 확인은 PowerShell에서 다음을 입력한다.

```powershell
python --version
git --version
```

Python 명령이 없으면 Python 설치 시 “Add Python to PATH”를 선택한 후 PowerShell을 새로 연다. Git 명령이 없으면 Git for Windows를 설치한 후 터미널을 새로 연다.

## 3. GitHub 저장소 확인과 main 브랜치

브라우저에서 각 저장소 주소를 연다.

- AI/API: https://github.com/Workshop-Koharu/Aura-AI
- 웹앱: https://github.com/Workshop-Koharu/Aura-AI-Web

404가 뜨면 저장소가 없다는 뜻일 수도 있지만, 비공개 저장소에 로그인 권한이 없을 때도 404가 표시될 수 있다. 먼저 GitHub 오른쪽 위 프로필이 올바른 계정인지 확인한다. 저장소 Settings → Collaborators/Manage access에서 계정 권한을 확인한다. 저장소 이름과 owner를 그대로 확인한다.

저장소가 확인된 다음 PowerShell에서:

```powershell
cd C:\\Users\\L\\Downloads\\Koharu\\Aura-AI
git status
git remote -v
git branch --show-current
```

원격 저장소가 없다면 저장소 페이지의 초록색 Code 버튼에서 HTTPS 주소를 복사한 후:

```powershell
git remote add origin https://github.com/Workshop-Koharu/Aura-AI.git
```

이미 origin이 있으면 `git remote set-url origin https://github.com/Workshop-Koharu/Aura-AI.git`로 주소를 수정한다. 주소는 실제 저장소 소유자/이름이 맞는지 먼저 확인해야 한다.

현재 브랜치가 main이 아니고 저장소에 main 브랜치가 존재한다면:

```powershell
git fetch origin
git switch main
git pull --ff-only origin main
```

초기 저장소라 main 브랜치가 아직 없으면 GitHub 저장소에서 기본 브랜치를 확인한 뒤, 프로젝트 소유자가 허용한 절차로 main을 만든다. 기존 프로젝트의 파일을 무작정 덮어쓰지 않는다.

변경사항을 커밋하고 올릴 때:

```powershell
git status
git add README.md docs app tests pyproject.toml .gitignore .env.example
git diff --cached
git commit -m "Add Aura AI API foundation and deployment guide"
git push -u origin main
```

GitHub에 기존 프로젝트 파일이 이미 있다면 먼저 `git pull --rebase origin main`으로 충돌 여부를 해결한다. `.env`, API 키, 토큰, 비밀번호 파일은 절대 add하지 않는다. `.env.example`에는 실제 비밀 값이 아니라 예시 값만 둔다.

## 4. API 로컬 환경 만들기

PowerShell에서 API 저장소 폴더로 이동한다.

```powershell
cd C:\\Users\\L\\Downloads\\Koharu\\Aura-AI
python -m venv .venv
.\\.venv\\Scripts\\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[dev]"
```

PowerShell이 스크립트 실행을 차단하면 우선 현재 창에서만 다음을 적용하고 가상환경 활성화를 다시 시도한다.

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\\.venv\\Scripts\\Activate.ps1
```

정책을 컴퓨터 전체에 영구 변경할 필요는 없다. 가상환경이 활성화되면 프롬프트 앞에 `(.venv)`가 표시된다.

## 5. 테스트 실행

정적 스타일 검사:

```powershell
ruff check .
```

자동 테스트:

```powershell
pytest -q
```

예상되는 기본 테스트는 `GET /`와 `GET /health`가 HTTP 200을 반환하는지 확인한다. 테스트가 실패하면 오류 메시지의 첫 번째 traceback과 실패한 assertion을 읽는다. 의존성 설치 오류라면 4단계를 다시 확인한다. 모듈을 찾을 수 없다는 오류라면 저장소 루트에서 명령을 실행했는지 확인한다.

API 서버 실행:

```powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

브라우저에서 다음 주소를 연다.

- http://127.0.0.1:8000/
- http://127.0.0.1:8000/health
- http://127.0.0.1:8000/docs

정상이라면 health 응답에 `{"status":"ok"}`가 보인다. 서버 종료는 터미널에서 Ctrl+C를 누른다.

## 6. Render에 FastAPI 서비스 만들기

먼저 API 코드가 접근 가능한 GitHub 저장소의 main 브랜치에 있어야 한다. Render가 코드를 가져올 수 있도록 Render 대시보드에서 GitHub 연결을 승인한다.

1. https://dashboard.render.com/ 를 연다.
2. Aura AI를 위한 올바른 workspace를 선택한다.
3. New + → Web Service를 누른다.
4. Git Provider에서 올바른 API 저장소를 선택한다. 저장소가 목록에 없다면 GitHub 연결의 저장소 권한을 갱신한다.
5. Name: `aura-ai-api`
6. Branch: `main`
7. Runtime: `Python`
8. Build Command: `pip install -e ".[dev]"` (운영 배포에서는 개발 의존성을 제외하고 싶다면 `pip install .` 사용)
9. Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
10. 인스턴스 지역은 사용자의 주요 사용자와 가까운 곳을 선택한다. 한국 사용자가 중심이면 제공되는 지역 중 Singapore가 일반적으로 가까운 선택지다.
11. 무료 플랜은 유휴 시 잠들거나 사용량/성능 제약이 있을 수 있다. 운영 안정성이 필요하면 가격과 제한을 검토한다.
12. Create Web Service를 누르고 Logs에서 설치·시작 로그를 확인한다.

서비스 설정에 환경변수를 추가하려면 Environment 탭을 연다. 처음에는 `AURA_ENVIRONMENT=production`과 필요한 CORS origin만 추가한다. 실제 웹앱 도메인을 아직 모르면 임시값을 넣기보다 배포 URL을 얻은 후 설정한다.

배포가 끝나면 Render가 표시하는 `https://....onrender.com` 주소를 기록한다. 다음을 확인한다.

- `https://서비스주소/health`
- `https://서비스주소/docs`

Render 로그에 “Application startup complete”가 보이지 않으면 Build/Deploy 로그의 첫 번째 오류를 확인한다. 시작 명령에 `$PORT`가 있어야 하며, 호스트는 `0.0.0.0`이어야 외부 요청을 받을 수 있다.

## 7. Vercel 웹 프로젝트 설정

프로젝트 `aura-ai-web`은 계정에 생성되었지만 소스 저장소 연결과 실제 배포는 별개다.

1. https://vercel.com/dashboard 를 연다.
2. `aura-ai-web` 프로젝트를 선택한다.
3. Settings → Git에서 Connect Git Repository를 누른다.
4. 웹앱 저장소 `Aura-AI-Web`을 선택한다. 이름과 owner가 실제 저장소와 일치하는지 확인한다.
5. Framework Preset을 실제 웹앱 프레임워크에 맞춘다. Next.js가 아니라면 잘못 감지된 설정을 수정한다.
6. Root Directory를 웹앱의 실제 루트로 설정한다. 모노레포라면 웹앱 폴더를 지정한다.
7. Build Command / Install Command는 프로젝트의 package.json과 lockfile에 맞춘다. 실제로 존재하지 않는 스크립트를 임의로 입력하지 않는다.
8. Settings → Environment Variables에 웹앱에서 사용할 API URL을 추가한다. 이 프로젝트는 Next.js이므로 `NEXT_PUBLIC_API_BASE_URL`을 사용한다. Cloudflare Connector가 연결되기 전 테스트는 `https://aura-ai-api-1gt5.onrender.com`을 넣고, Tunnel을 사용할 준비가 된 뒤 `https://api-aura.koharu.live`로 바꾼다.
9. 값을 저장한 뒤 Deployments에서 새 배포를 실행한다.

### 현재 Vercel 권한 차단 해결
Vercel API를 통해 `aura.koharu.live`를 프로젝트에 등록하려 했으나 현재 연결된 Vercel 인증이 프로젝트 소유 범위에 대해 HTTP 403을 반환했다. Vercel Dashboard → `aura-ai-web` → Settings → Domains에서 `aura.koharu.live`을 직접 추가한다. 그런 다음 Vercel이 표시하는 DNS 안내를 확인한다. 현재 Cloudflare에는 `aura.koharu.live` CNAME → `cname.vercel-dns.com` (DNS only) 레코드가 있다. Vercel이 다른 target 또는 TXT 검증 레코드를 표시하면 **Vercel 화면의 최신 지시값을 우선**하고, 검증이 완료될 때까지 도메인을 연결 완료로 간주하지 않는다. Settings → Git에서 `Workshop-Koharu/Aura-AI-Web` 저장소의 `main` 브랜치도 연결한다. 연결이 완료되면 Vercel에서 자동 배포를 확인한다.
10. 빌드 로그가 성공하면 배포 URL을 연다.

주의: `NEXT_PUBLIC_*` 또는 `VITE_*` 값은 브라우저에 노출된다. 비밀 키, Cloudflare 토큰, 모델 제공자 API 키를 여기에 넣으면 안 된다. 브라우저에는 공개 가능한 API base URL만 둔다.

CORS는 API 서버에서 허용해야 한다. Render 환경변수 `AURA_CORS_ORIGINS`에 Vercel 실제 도메인을 정확하게 넣는다. 예: `https://aura-ai-web.vercel.app` (실제 생성된 도메인 확인 후 입력). 여러 origin은 쉼표로 구분한다. 와일드카드 `*`는 인증 쿠키를 사용하는 운영 환경에서 피한다.

## 8. Cloudflare Tunnel이 하는 일과 필요한 값

Tunnel을 실제로 켜려면 아래 값이 필요하다.

- Cloudflare account ID
- Tunnel 이름 및 Tunnel ID
- Tunnel connector를 실행할 컴퓨터/서버
- 라우팅할 공개 hostname (예: `api.example.com`)
- 해당 hostname을 관리하는 도메인의 DNS가 Cloudflare에 연결되어 있어야 함
- 목적지 서비스 주소 (예: `http://localhost:8000` 또는 배포된 API의 HTTPS 주소)

자신의 도메인이 없다면 Cloudflare의 사용자 지정 hostname 방식은 완성할 수 없다. Quick Tunnel은 임시 테스트용이며 고정 운영 도메인의 대체물이 아니다.

### 8.1 대시보드에서 터널 생성

1. https://one.dash.cloudflare.com/ 을 연다.
2. 올바른 계정을 선택한다.
3. Networks → Tunnels (대시보드 메뉴명이 바뀌었을 수 있음)를 연다.
4. Create a tunnel을 누른다.
5. Cloudflared를 선택하고 이름을 `aura-ai-api`로 지정한다.
6. 화면에서 운영체제에 맞는 설치·실행 명령을 확인한다.
7. connector token은 비밀번호처럼 취급한다. 채팅·GitHub·문서에 값을 붙여 넣지 않는다.
8. 해당 명령을 실제로 터널을 유지할 서버에서 실행한다. 노트북에서 실행하면 노트북이 꺼질 때 터널도 끊긴다.
9. Connector가 Healthy/Connected로 보이는지 확인한다.

### 8.2 Public Hostname과 origin 설정

1. 생성한 Tunnel의 Public Hostnames 또는 Routes 설정을 연다.
2. hostname에 본인이 관리하는 도메인의 API 서브도메인을 입력한다.
3. Service type은 목적지에 맞게 HTTP 또는 HTTPS를 선택한다.
4. 목적지 주소와 포트를 정확히 입력한다. API가 Render에 있다면 Render의 공개 HTTPS 주소를 origin으로 쓸 수 있지만, 이 경우 Tunnel이 Render로 다시 전달하는 프록시 구조가 된다.
5. 저장한 뒤 DNS 레코드와 Tunnel 상태를 확인한다.
6. `https://api.example.com/health` 같은 health 경로를 브라우저에서 테스트한다.

도메인이 Cloudflare DNS에 없다면 hostname 라우팅을 구성하기 전에 도메인을 Cloudflare에 추가하고 nameserver/DNS 절차를 완료해야 한다. 기존 도메인의 DNS를 바꾸면 다른 서비스가 영향을 받을 수 있으므로 기존 레코드를 먼저 기록한다.

### 8.3 터널 토큰 보안

- 토큰은 비밀 값이다. GitHub 저장소에 절대 커밋하지 않는다.
- Render 환경변수나 로컬 환경변수에 넣을 때도 접근 권한을 최소화한다.
- 공개 저장소에 노출되었다면 즉시 토큰을 회전/폐기한다.
- 실제 origin을 사용할 수 없는 상태에서 임의의 도메인이나 서비스를 만들지 않는다.

## 9. Vercel → API 연결 테스트

먼저 API의 실제 URL을 확인한다. Render 직접 연결이라면 Render URL, Cloudflare를 거친다면 공개 API hostname을 사용한다.

PowerShell에서:

```powershell
$ApiBase = "https://실제-API-주소"
Invoke-RestMethod "$ApiBase/health"
```

정상 응답이 나오면 API 네트워크 경로가 동작한다. 다음으로 Vercel 프로젝트의 API base URL을 설정하고 재배포한다. 브라우저 개발자 도구(F12) → Network에서 API 요청을 선택한다.

- 요청 URL이 기대한 API URL인지 확인한다.
- HTTP status가 200인지 확인한다.
- CORS 오류라면 Render의 `AURA_CORS_ORIGINS`에 현재 Vercel 도메인이 있는지 확인한다.
- 404라면 URL 경로가 올바른지 확인한다.
- 502/503이라면 Render 배포 상태, 시작 로그, Tunnel connector 상태를 확인한다.
- 브라우저가 HTTPS 페이지에서 HTTP API를 호출하면 Mixed Content로 차단될 수 있으므로 API도 HTTPS를 사용한다.

## 10. GitHub Actions로 테스트 자동화(선택)

프로젝트 루트에 `.github/workflows/tests.yml` 파일을 만들고 다음을 넣으면 main에 push하거나 Pull Request를 만들 때 테스트를 자동 실행할 수 있다.

```yaml
name: API tests
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: python -m pip install --upgrade pip
      - run: pip install -e ".[dev]"
      - run: ruff check .
      - run: pytest -q
```

파일을 저장한 뒤 3단계의 Git 명령으로 main에 올린다. GitHub 저장소의 Actions 탭에서 실행 상태를 확인한다. 초록색 체크는 작업 성공, 빨간색 X는 실패를 뜻한다. 실패한 실행을 열고 로그에서 처음 나타나는 오류를 확인한다.

## 11. 흔한 문제 해결

### GitHub에서 저장소가 안 보임
- 로그인한 GitHub 계정 확인.
- 저장소 owner/name 철자 확인.
- 비공개 저장소라면 collaborator/team 권한과 앱 권한 확인.
- 올바른 저장소가 확정되기 전 다른 저장소에 push하지 않는다.

### Render 빌드 실패
- Build Command와 Start Command를 다시 확인.
- Python 버전이 프로젝트와 호환되는지 확인.
- `pyproject.toml`이 저장소 루트에 있는지 확인.
- 로그에서 실제 오류를 읽는다. 추측으로 패키지를 무작정 추가하지 않는다.

### Vercel 빌드 실패
- 웹앱 저장소의 `package.json`과 lockfile이 존재하는지 확인.
- Root Directory가 실제 웹앱 위치인지 확인.
- package manager와 install/build command를 일치시킨다.
- API URL은 공개 가능한 값만 환경변수로 설정한다.

### CORS 오류
- 허용 origin에 scheme(`https://`)과 도메인을 정확히 넣는다.
- 끝의 경로(`/chat`)는 origin 값에 포함하지 않는다.
- 환경변수 변경 후 Render 서비스를 재시작/재배포한다.

### Tunnel이 연결되지 않음
- Connector 프로세스가 실행 중인지 확인.
- Tunnel token이 정확한지 확인하되, 외부에 공개하지 않는다.
- Tunnel이 Healthy인지 확인.
- hostname DNS가 Cloudflare를 가리키는지 확인.
- origin URL과 포트가 실제 서비스 주소인지 확인.
- HTTPS origin을 쓸 때 인증서 검증을 끄는 설정을 해결책으로 사용하지 않는다.

## 12. 최종 점검표

- [ ] 올바른 API 저장소와 웹 저장소가 GitHub에서 보임
- [ ] main 브랜치가 최신 코드 포함
- [ ] `ruff check .` 통과
- [ ] `pytest -q` 통과
- [ ] 로컬 `/health` 응답 성공
- [ ] Render 빌드 성공 및 `/health` 응답 성공
- [ ] Vercel 프로젝트가 올바른 Git 저장소와 연결됨
- [ ] Vercel 배포 성공
- [ ] API CORS에 실제 Vercel origin 등록
- [ ] Cloudflare Tunnel 사용 시 connector Healthy
- [ ] 공개 API hostname이 HTTPS로 `/health` 응답
- [ ] 비밀 값이 Git history와 클라이언트 환경변수에 없음
- [ ] 실제 브라우저에서 웹앱 → API 호출 성공

## 13. 배포 순서 요약

1. GitHub 저장소 주소와 권한 확인.
2. 로컬 테스트 실행.
3. 코드와 문서를 main에 push.
4. Render에서 API 서비스 생성 및 health 확인.
5. Vercel에서 웹 저장소 연결 및 배포.
6. Vercel 환경변수와 Render CORS 설정.
7. 필요할 때만 Cloudflare Tunnel과 사용자 지정 DNS를 연결.
8. 브라우저에서 최종 end-to-end 테스트.

이 순서가 가장 문제를 좁히기 쉽다. 한 번에 세 플랫폼을 동시에 바꾸면 어느 구간에서 실패했는지 파악하기 어렵다.
