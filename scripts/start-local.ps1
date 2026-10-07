param([int]$BackendPort = 8002, [int]$FrontendPort = 5176)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$backendRoot = Join-Path $projectRoot 'backend'
$frontendRoot = Join-Path $projectRoot 'frontend'
$logRoot = Join-Path $projectRoot 'tmp'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
$pythonCommand = (Get-Command python).Source
$nodeCommand = (Get-Command node).Source
$workspacePackages = Join-Path $projectRoot '.runtime\python'
if (Test-Path -LiteralPath $workspacePackages) { $env:PYTHONPATH = $workspacePackages }
$env:AIDSO_BACKEND_URL = "http://127.0.0.1:$BackendPort"
$backendProcess = Start-Process -FilePath $pythonCommand -ArgumentList @('-u', '-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', "$BackendPort") -WorkingDirectory $backendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'backend.log') -RedirectStandardError (Join-Path $logRoot 'backend-error.log') -PassThru
try {
    $ready = $false
    for ($attempt = 0; $attempt -lt 60; $attempt++) {
        if ($backendProcess.HasExited) { throw 'API failed to start. Check tmp/backend-error.log.' }
        try { $ready = (Invoke-RestMethod "http://127.0.0.1:$BackendPort/api/health").status -eq 'ok' } catch { }
        if ($ready) { break }
        Start-Sleep -Seconds 1
    }
    if (-not $ready) { throw 'API startup timed out. Check tmp/backend-error.log.' }
    $workerProcess = Start-Process -FilePath $pythonCommand -ArgumentList @('-u', 'worker/worker.py') -WorkingDirectory $backendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'worker.log') -RedirectStandardError (Join-Path $logRoot 'worker-error.log') -PassThru
    $frontendProcess = Start-Process -FilePath $nodeCommand -ArgumentList @('node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', "$FrontendPort", '--strictPort') -WorkingDirectory $frontendRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'frontend.log') -RedirectStandardError (Join-Path $logRoot 'frontend-error.log') -PassThru
    [PSCustomObject]@{ API = $backendProcess.Id; Worker = $workerProcess.Id; Frontend = $frontendProcess.Id } | ConvertTo-Json | Set-Content (Join-Path $logRoot 'local-processes.json')
    Write-Output "App: http://127.0.0.1:$FrontendPort"
    Write-Output "API: http://127.0.0.1:$BackendPort/api/health"
    Write-Output 'Process IDs are saved in tmp/local-processes.json; stop these processes to shut down.'
} catch {
    if (-not $backendProcess.HasExited) { Stop-Process -Id $backendProcess.Id }
    throw
}
