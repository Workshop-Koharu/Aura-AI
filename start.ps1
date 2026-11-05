$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:CUDA_VISIBLE_DEVICES = ""
$env:OMP_NUM_THREADS = "4"
$env:MKL_NUM_THREADS = "4"
$env:OPENBLAS_NUM_THREADS = "4"
$env:PYTHONUTF8 = "1"
py -3.14 -m uvicorn api.main:app --host 127.0.0.1 --port 8000
