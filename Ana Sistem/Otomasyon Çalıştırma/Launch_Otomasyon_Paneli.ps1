$ErrorActionPreference = "Stop"

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$appPath = Join-Path $scriptDir "app.py"
$controlDir = Join-Path $scriptDir ".control"
$panelStatePath = Join-Path $controlDir "panel_server.json"
$stdoutLogPath = Join-Path $controlDir "panel_stdout.log"
$stderrLogPath = Join-Path $controlDir "panel_stderr.log"
$panelHost = "127.0.0.1"
$panelPort = 8501
$panelUrl = "http://$panelHost`:$panelPort"

New-Item -ItemType Directory -Force -Path $controlDir | Out-Null

function Show-LaunchMessage {
    param(
        [string]$message,
        [string]$title = "Otomasyon Paneli"
    )

    try {
        Add-Type -AssemblyName PresentationFramework -ErrorAction SilentlyContinue | Out-Null
        [void][System.Windows.MessageBox]::Show($message, $title)
    } catch {
    }
}

function Test-TcpPort {
    param(
        [string]$HostName,
        [int]$Port,
        [int]$TimeoutMs = 700
    )

    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($HostName, $Port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($TimeoutMs, $false)) {
            return $false
        }
        $client.EndConnect($async)
        return $true
    } catch {
        return $false
    } finally {
        $client.Close()
    }
}

function New-ArgumentString {
    param([string[]]$Parts)

    $encoded = foreach ($part in $Parts) {
        if ($null -eq $part) {
            '""'
        } elseif ($part -match '[\s"]') {
            '"' + $part + '"'
        } else {
            $part
        }
    }
    return ($encoded -join " ")
}

function Test-StreamlitImport {
    param(
        [string]$FilePath,
        [string[]]$Arguments
    )

    try {
        & $FilePath @Arguments *> $null
        return ($LASTEXITCODE -eq 0)
    } catch {
        return $false
    }
}

function Get-LaunchSpec {
    $commonArgs = @(
        "run",
        $appPath,
        "--server.headless", "true",
        "--server.address", $panelHost,
        "--server.port", [string]$panelPort,
        "--browser.gatherUsageStats", "false"
    )

    $streamlitCommand = Get-Command streamlit -ErrorAction SilentlyContinue
    if ($streamlitCommand) {
        return @{
            FilePath = $streamlitCommand.Source
            Arguments = (New-ArgumentString -Parts $commonArgs)
            Source = "streamlit.exe"
        }
    }

    $pyCommand = Get-Command py -ErrorAction SilentlyContinue
    if ($pyCommand -and (Test-StreamlitImport -FilePath $pyCommand.Source -Arguments @("-3.13", "-c", "import streamlit"))) {
        return @{
            FilePath = $pyCommand.Source
            Arguments = (New-ArgumentString -Parts (@("-3.13", "-m", "streamlit") + $commonArgs))
            Source = "py -3.13"
        }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand -and (Test-StreamlitImport -FilePath $pythonCommand.Source -Arguments @("-c", "import streamlit"))) {
        return @{
            FilePath = $pythonCommand.Source
            Arguments = (New-ArgumentString -Parts (@("-m", "streamlit") + $commonArgs))
            Source = "python -m streamlit"
        }
    }

    return $null
}

function Get-LivePanelState {
    if (-not (Test-Path $panelStatePath)) {
        return $null
    }

    try {
        $raw = Get-Content -Path $panelStatePath -Raw -Encoding UTF8
        $state = $raw | ConvertFrom-Json
    } catch {
        Remove-Item -Path $panelStatePath -Force -ErrorAction SilentlyContinue
        return $null
    }

    $pidText = [string]$state.pid
    if ($pidText -notmatch '^\d+$') {
        Remove-Item -Path $panelStatePath -Force -ErrorAction SilentlyContinue
        return $null
    }

    try {
        Get-Process -Id ([int]$pidText) -ErrorAction Stop | Out-Null
        return $state
    } catch {
        Remove-Item -Path $panelStatePath -Force -ErrorAction SilentlyContinue
        return $null
    }
}

function Open-PanelUrl {
    param([string]$Url)
    Start-Process $Url | Out-Null
}

if (-not (Test-Path $appPath)) {
    Show-LaunchMessage -message "app.py bulunamadi: $appPath"
    exit 1
}

$liveState = Get-LivePanelState
if ($liveState) {
    $existingUrl = [string]($liveState.url)
    if ([string]::IsNullOrWhiteSpace($existingUrl)) {
        $existingUrl = $panelUrl
    }

    $existingPortText = [string]($liveState.port)
    $existingPort = $panelPort
    if ($existingPortText -match '^\d+$') {
        $existingPort = [int]$existingPortText
    }

    for ($i = 0; $i -lt 20; $i++) {
        if (Test-TcpPort -HostName $panelHost -Port $existingPort) {
            Open-PanelUrl -Url $existingUrl
            exit 0
        }
        Start-Sleep -Milliseconds 500
    }
}

if (Test-TcpPort -HostName $panelHost -Port $panelPort) {
    Open-PanelUrl -Url $panelUrl
    exit 0
}

$launchSpec = Get-LaunchSpec
if ($null -eq $launchSpec) {
    Show-LaunchMessage -message "Streamlit bulunamadi. Once streamlit kurulumunu kontrol et."
    exit 1
}

if (Test-Path $stdoutLogPath) {
    Remove-Item -Path $stdoutLogPath -Force -ErrorAction SilentlyContinue
}
if (Test-Path $stderrLogPath) {
    Remove-Item -Path $stderrLogPath -Force -ErrorAction SilentlyContinue
}

$process = Start-Process `
    -FilePath $launchSpec.FilePath `
    -ArgumentList $launchSpec.Arguments `
    -WorkingDirectory $scriptDir `
    -WindowStyle Hidden `
    -RedirectStandardOutput $stdoutLogPath `
    -RedirectStandardError $stderrLogPath `
    -PassThru

[ordered]@{
    pid = $process.Id
    port = $panelPort
    url = $panelUrl
    app = $appPath
    launcher = $launchSpec.Source
    started_at = (Get-Date).ToString("s")
} | ConvertTo-Json | Set-Content -Path $panelStatePath -Encoding UTF8

$ready = $false
for ($i = 0; $i -lt 90; $i++) {
    if (Test-TcpPort -HostName $panelHost -Port $panelPort) {
        $ready = $true
        break
    }

    try {
        Get-Process -Id $process.Id -ErrorAction Stop | Out-Null
    } catch {
        break
    }

    Start-Sleep -Milliseconds 500
}

if (-not $ready) {
    Remove-Item -Path $panelStatePath -Force -ErrorAction SilentlyContinue

    $detail = ""
    if (Test-Path $stderrLogPath) {
        $tail = Get-Content -Path $stderrLogPath -Tail 20 -ErrorAction SilentlyContinue
        if ($tail) {
            $detail = ($tail -join [Environment]::NewLine)
        }
    }
    if (-not $detail -and (Test-Path $stdoutLogPath)) {
        $tail = Get-Content -Path $stdoutLogPath -Tail 20 -ErrorAction SilentlyContinue
        if ($tail) {
            $detail = ($tail -join [Environment]::NewLine)
        }
    }

    $message = "Otomasyon Paneli baslatilamadi veya cevap vermedi."
    if ($detail) {
        $message += [Environment]::NewLine + [Environment]::NewLine + $detail
    }

    Show-LaunchMessage -message $message
    exit 1
}

Open-PanelUrl -Url $panelUrl
exit 0
