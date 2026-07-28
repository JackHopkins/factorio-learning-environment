param(
    [string]$SshHost = 'raider-codex',
    [int]$LocalModelPort = 18080,
    [int]$RemoteModelPort = 8080,
    [int]$EnvdPort = 8172,
    [int]$RconPort = 27000,
    [string]$TaskId = 'milestone_research_automation_v1',
    [int]$MaxTurns = 0,
    [int]$MaxOutputTokens = 2048,
    [switch]$Preflight,
    [switch]$KeepServices
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'
$runtime = Join-Path $repoRoot 'runtime\raider-eval'
New-Item -ItemType Directory -Force -Path $runtime | Out-Null

if (-not (Test-Path -LiteralPath $python)) {
    throw "Factorio environment Python was not found: $python"
}

function Test-JsonEndpoint {
    param([string]$Uri)
    try {
        Invoke-RestMethod -Uri $Uri -TimeoutSec 3 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Wait-JsonEndpoint {
    param(
        [string]$Uri,
        [int]$TimeoutSeconds = 60
    )
    $deadline = [DateTime]::UtcNow.AddSeconds($TimeoutSeconds)
    while ([DateTime]::UtcNow -lt $deadline) {
        if (Test-JsonEndpoint -Uri $Uri) {
            return
        }
        Start-Sleep -Milliseconds 500
    }
    throw "Endpoint did not become ready within $TimeoutSeconds seconds: $Uri"
}

$ownedTunnel = $null
$ownedEnvdListenerPid = $null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$output = Join-Path $runtime "factorio-$TaskId-$stamp.json"

try {
    $modelModelsUrl = "http://127.0.0.1:$LocalModelPort/v1/models"
    if (-not (Test-JsonEndpoint -Uri $modelModelsUrl)) {
        $sshOut = Join-Path $runtime "ssh-tunnel-$stamp.stdout.log"
        $sshErr = Join-Path $runtime "ssh-tunnel-$stamp.stderr.log"
        $sshArgs = @(
            '-N',
            '-o', 'BatchMode=yes',
            '-o', 'ExitOnForwardFailure=yes',
            '-o', 'ServerAliveInterval=15',
            '-o', 'ServerAliveCountMax=3',
            '-L', "127.0.0.1:${LocalModelPort}:127.0.0.1:${RemoteModelPort}",
            $SshHost
        )
        $ownedTunnel = Start-Process `
            -FilePath 'ssh.exe' `
            -ArgumentList $sshArgs `
            -RedirectStandardOutput $sshOut `
            -RedirectStandardError $sshErr `
            -WindowStyle Hidden `
            -PassThru
        try {
            Wait-JsonEndpoint -Uri $modelModelsUrl -TimeoutSeconds 20
        }
        catch {
            if (Test-Path -LiteralPath $sshErr) {
                Get-Content -LiteralPath $sshErr -Tail 80
            }
            throw
        }
    }

    $envdHealthUrl = "http://127.0.0.1:$EnvdPort/v1/health"
    if (-not (Test-JsonEndpoint -Uri $envdHealthUrl)) {
        $envdOut = Join-Path $runtime "factorio-envd-$stamp.stdout.log"
        $envdErr = Join-Path $runtime "factorio-envd-$stamp.stderr.log"
        $envdArgs = @(
            '-m', 'fle.envd',
            '--host', '127.0.0.1',
            '--port', "$EnvdPort",
            '--factorio-address', '127.0.0.1',
            '--rcon-ports', "$RconPort"
        )
        Start-Process `
            -FilePath $python `
            -ArgumentList $envdArgs `
            -WorkingDirectory $repoRoot `
            -RedirectStandardOutput $envdOut `
            -RedirectStandardError $envdErr `
            -WindowStyle Hidden | Out-Null
        try {
            Wait-JsonEndpoint -Uri $envdHealthUrl -TimeoutSeconds 45
        }
        catch {
            if (Test-Path -LiteralPath $envdErr) {
                Get-Content -LiteralPath $envdErr -Tail 120
            }
            throw
        }
        $ownedEnvdListenerPid = (
            Get-NetTCPConnection -LocalPort $EnvdPort -State Listen |
                Select-Object -First 1 -ExpandProperty OwningProcess
        )
    }

    $runnerArgs = @(
        '-m', 'fle.eval.remote_agent',
        '--envd-url', "http://127.0.0.1:$EnvdPort",
        '--model-base-url', "http://127.0.0.1:$LocalModelPort/v1",
        '--task-id', $TaskId,
        '--max-output-tokens', "$MaxOutputTokens",
        '--output', $output,
        '--quiet'
    )
    if ($MaxTurns -gt 0) {
        $runnerArgs += @('--max-turns', "$MaxTurns")
    }
    if ($Preflight) {
        $runnerArgs += '--preflight'
    }

    & $python @runnerArgs
    $runnerExit = $LASTEXITCODE
    Write-Host "Factorio agent result: $output"
    exit $runnerExit
}
finally {
    if (-not $KeepServices) {
        if ($null -ne $ownedEnvdListenerPid) {
            Stop-Process -Id $ownedEnvdListenerPid -ErrorAction SilentlyContinue
        }
        if ($null -ne $ownedTunnel -and -not $ownedTunnel.HasExited) {
            Stop-Process -Id $ownedTunnel.Id -ErrorAction SilentlyContinue
        }
    }
}
