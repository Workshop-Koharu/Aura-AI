$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$ModelRoot = Join-Path $Root "kaggle\aura-ai-korean-chat-sft-v2\outputs\Aura-AI"
$SecretPath = Join-Path $Root ".aura-gateway-secret"
$CredentialPath = Join-Path $env:USERPROFILE ".cloudflared\aura-ai-api.json"
if (!(Test-Path $SecretPath)) { throw "Missing local inference secret file." }
if (!(Test-Path $CredentialPath)) { throw "Missing Cloudflare tunnel credentials." }
$env:AURA_GATEWAY_SECRET = (Get-Content $SecretPath -Raw).Trim()
$env:AURA_MODEL_DIR = $ModelRoot
$health = $false
try { $health = (Invoke-RestMethod "http://127.0.0.1:8000/health" -TimeoutSec 2).ok } catch {}
if (!$health) {
  Start-Process -FilePath "py.exe" -ArgumentList @("-3.14","-m","uvicorn","inference_server:app","--host","127.0.0.1","--port","8000","--workers","1") -WorkingDirectory $Root -WindowStyle Hidden
}
$tunnelRunning = Get-CimInstance Win32_Process -Filter "name='cloudflared.exe'" | Where-Object { $_.CommandLine -match 'aura-ai-api' }
if (!$tunnelRunning) {
  Start-Process -FilePath "cloudflared.exe" -ArgumentList @("tunnel","--credentials-file",$CredentialPath,"run","aura-ai-api") -WindowStyle Hidden
}
