$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot
$env:CUDA_VISIBLE_DEVICES = ""
$env:OMP_NUM_THREADS = "4"
$env:MKL_NUM_THREADS = "4"
py -3.14 -m mcp_server.http
