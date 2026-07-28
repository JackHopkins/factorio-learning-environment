param(
    [string]$EnvdUrl = 'http://127.0.0.1:8172',
    [string]$ApiBaseUrl = 'https://api.deepseek.com',
    [string[]]$Models = @('deepseek-v4-flash', 'deepseek-v4-pro'),
    [int]$Attempts = 1,
    [int]$ToolErrorRetries = 0,
    [ValidateSet('', 'development', 'validation', 'test')]
    [string]$Split = '',
    [string]$OutputDirectory = 'benchmark/results'
)

$ErrorActionPreference = 'Stop'
$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..\..')
$python = Join-Path $repoRoot '.venv\Scripts\python.exe'

if (-not $env:DEEPSEEK_API_KEY) {
    throw 'Set DEEPSEEK_API_KEY in the environment before running this script.'
}
if (-not (Test-Path -LiteralPath $python)) {
    throw "Factorio environment Python was not found: $python"
}

try {
    Invoke-RestMethod -Uri "$EnvdUrl/v1/health" -TimeoutSec 5 | Out-Null
}
catch {
    throw "factorio-envd is not reachable at $EnvdUrl"
}

$outputRoot = Join-Path $repoRoot $OutputDirectory
New-Item -ItemType Directory -Force -Path $outputRoot | Out-Null
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

foreach ($model in $Models) {
    $safeModel = $model -replace '[^A-Za-z0-9._-]', '-'
    $output = Join-Path $outputRoot "$safeModel-$stamp.json"
    $arguments = @(
        '-m', 'fle.eval.benchmark_agent',
        '--envd-url', $EnvdUrl,
        '--model-base-url', $ApiBaseUrl,
        '--model', $model,
        '--provider', 'deepseek-api',
        '--suite', 'api_microtasks_v1',
        '--status', 'ready',
        '--attempts', "$Attempts",
        '--tool-error-retries', "$ToolErrorRetries",
        '--output', $output
    )
    if ($Split) {
        $arguments += @('--split', $Split)
    }

    & $python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "Benchmark failed for $model with exit code $LASTEXITCODE"
    }
}
