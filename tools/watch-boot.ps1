# Watches what the phone exposes while it is being flashed / booted.
#
# There is no UART on umi and the ABL gives us no log channel, so "listening to
# logs" here means: watch USB enumeration, fastboot presence and the CDC-ACM COM
# port, and capture whatever comes out of that port. Everything is timestamped
# and appended to one file so a failed boot still leaves a record.
#
#   .\watch-boot.ps1 -Minutes 30
#
param(
    [int]$Minutes = 30,
    [string]$LogPath = "$PSScriptRoot\..\out\watch.log",
    [int]$SerialSeconds = 180
)

$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogPath) | Out-Null

function Log([string]$msg) {
    $line = "{0}  {1}" -f (Get-Date -Format 'HH:mm:ss.fff'), $msg
    Write-Host $line
    Add-Content -Path $LogPath -Value $line -Encoding utf8
}

function PhoneDevices {
    Get-PnpDevice -PresentOnly -ErrorAction SilentlyContinue | Where-Object {
        $_.InstanceId -match 'VID_(18D1|2717|05C6|1D6B|2C7C|0525)' -or
        $_.FriendlyName -match 'USB Serial|CDC|Gadget|Android'
    } | ForEach-Object { "$($_.FriendlyName) [$($_.InstanceId)]" }
}

function ComPorts {
    [System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object
}

Log "watching for $Minutes min, log: $LogPath"
Log ("baseline devices: " + ((PhoneDevices) -join '; '))
Log ("baseline ports: " + ((ComPorts) -join ', '))

$baselinePorts = ComPorts
$deadline = (Get-Date).AddMinutes($Minutes)
$lastState = ''
$seenFastboot = $false
$captured = $false

while ((Get-Date) -lt $deadline) {
    $fb = (& fastboot devices 2>&1 | Out-String).Trim()
    $devs = (PhoneDevices) -join '; '
    $ports = ComPorts
    $state = "fb=[$fb] usb=[$devs] com=[$($ports -join ',')]"

    if ($state -ne $lastState) {
        Log $state
        $lastState = $state
    }
    if ($fb -match 'fastboot') { $seenFastboot = $true }

    $newPorts = $ports | Where-Object { $baselinePorts -notcontains $_ }
    if (-not $captured -and $newPorts) {
        foreach ($p in $newPorts) {
            Log "new COM port $p -> capturing ${SerialSeconds}s at 115200"
            try {
                $sp = New-Object System.IO.Ports.SerialPort $p, 115200, 'None', 8, 'One'
                $sp.ReadTimeout = 2000
                $sp.DtrEnable = $true
                $sp.Open()
                $until = (Get-Date).AddSeconds($SerialSeconds)
                $buf = New-Object System.Text.StringBuilder
                while ((Get-Date) -lt $until) {
                    try { [void]$buf.Append($sp.ReadExisting()); Start-Sleep -Milliseconds 200 } catch { Start-Sleep -Milliseconds 500 }
                }
                $sp.Close()
                $text = $buf.ToString()
                Log "captured $($text.Length) chars from $p"
                if ($text.Length -gt 0) {
                    Add-Content -Path $LogPath -Value "----- $p -----" -Encoding utf8
                    Add-Content -Path $LogPath -Value $text -Encoding utf8
                }
            } catch {
                Log "open $p failed: $($_.Exception.Message)"
            }
        }
        $captured = $true
    }

    Start-Sleep -Seconds 5
}

Log "done. fastboot seen: $seenFastboot, serial captured: $captured"
