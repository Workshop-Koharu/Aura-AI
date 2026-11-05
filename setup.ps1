$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) { throw "Python launcher is required." }
py -3.14 -c "import torch, fastapi, uvicorn, numpy, PIL, psutil, mcp" 2>$null
if ($LASTEXITCODE -ne 0) {
    py -3.14 -m pip install --upgrade pip
    py -3.14 -m pip install -r requirements.txt
}
New-Item -ItemType Directory -Force -Path data\text,data\image_text,data\audio_text,data\checkpoints,data\tokenizer | Out-Null
Write-Host "Aura dependencies and data folders are ready."
