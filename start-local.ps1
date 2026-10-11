$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host 'Grid Flex — synthetic microgrid scheduling demo' -ForegroundColor Cyan
python -c "import scipy; print('SciPy version:',scipy.__version__)"
if ($LASTEXITCODE -ne 0) { Write-Host 'Run: python -m pip install -r requirements.txt' -ForegroundColor Yellow; exit 1 }
Start-Process 'http://localhost:8000'
python server.py
