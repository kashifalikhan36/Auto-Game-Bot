#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Uninstalls the Interception keyboard/mouse filter driver on Windows 11.

.DESCRIPTION
    Reverses the steps performed by Install-Win11.ps1:
      1. Removes 'keyboard' / 'mouse' from class UpperFilters
      2. Stops and deletes the kernel services
      3. Deletes the driver files from System32\Drivers
      4. Removes the test certificate from Root and TrustedPublisher stores
      5. Disables Test Signing mode (bcdedit)
      6. Prompts for a reboot
#>

[CmdletBinding(SupportsShouldProcess)]
param()

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$CERT_SUBJECT = "CN=Interception Driver Test Cert, O=LocalDev, OU=GameBot"
$SYSTEM_DRV   = "$env:SystemRoot\System32\drivers"

$KBD_CLASS_GUID   = "{4D36E96B-E325-11CE-BFC1-08002BE10318}"
$MOUSE_CLASS_GUID = "{4D36E96F-E325-11CE-BFC1-08002BF6382B}"

function Write-Step([string]$m) { Write-Host "  ► $m" -ForegroundColor Yellow }
function Write-OK([string]$m)   { Write-Host "  ✓ $m" -ForegroundColor Green  }
function Write-Warn([string]$m) { Write-Host "  ⚠ $m" -ForegroundColor Magenta }

Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host "  Interception Driver Uninstaller - Windows 11 Edition"          -ForegroundColor Cyan
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
Write-Host ""

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 1 - Remove UpperFilters entries
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Removing UpperFilters registry entries…"

function Remove-UpperFilter {
    param([string]$ClassGuid, [string]$FilterName)

    $regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\$ClassGuid"
    if (-not (Test-Path $regPath)) { return }

    $current = (Get-ItemProperty -Path $regPath -Name UpperFilters -ErrorAction SilentlyContinue).UpperFilters
    if ($null -eq $current) { return }

    $newVal = $current | Where-Object { $_ -ne $FilterName }

    if ($newVal.Count -eq $current.Count) {
        Write-OK "'$FilterName' not found in UpperFilters [$ClassGuid] - nothing to do."
        return
    }

    Set-ItemProperty -Path $regPath -Name UpperFilters -Value $newVal -Type MultiString
    Write-OK "Removed '$FilterName' from UpperFilters [$ClassGuid]"
}

Remove-UpperFilter -ClassGuid $KBD_CLASS_GUID   -FilterName "keyboard"
Remove-UpperFilter -ClassGuid $MOUSE_CLASS_GUID -FilterName "mouse"

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2 - Stop and delete services
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Stopping and removing kernel services…"

foreach ($svcName in @("keyboard","mouse")) {
    $svc = Get-Service -Name $svcName -ErrorAction SilentlyContinue
    if ($svc) {
        try { & sc.exe stop $svcName 2>&1 | Out-Null } catch {}
        Start-Sleep -Milliseconds 300
        & sc.exe delete $svcName | Out-Null
        Write-OK "Service removed: $svcName"
    } else {
        Write-OK "Service '$svcName' not found - already removed."
    }
}

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 3 - Delete driver files
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Removing driver files…"

foreach ($fname in @("keyboard.sys","mouse.sys")) {
    $fp = Join-Path $SYSTEM_DRV $fname
    if (Test-Path $fp) {
        # Files locked at runtime - mark for deletion on next boot if needed
        try {
            Remove-Item $fp -Force
            Write-OK "Deleted: $fp"
        } catch {
            # Schedule deletion on next reboot via MoveFileEx
            Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class FileHelper {
    [DllImport("kernel32.dll", SetLastError=true, CharSet=CharSet.Unicode)]
    public static extern bool MoveFileEx(string lpExistingFileName, string lpNewFileName, uint dwFlags);
    public const uint MOVEFILE_DELAY_UNTIL_REBOOT = 0x4;
}
"@
            [FileHelper]::MoveFileEx($fp, $null, [FileHelper]::MOVEFILE_DELAY_UNTIL_REBOOT) | Out-Null
            Write-Warn "File in use - scheduled for deletion on next reboot: $fp"
        }
    } else {
        Write-OK "Already absent: $fp"
    }
}

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 4 - Remove test certificate
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Removing test certificate from trust stores…"

foreach ($storeName in @("Root","TrustedPublisher","My")) {
    $certPath = "Cert:\LocalMachine\$storeName"
    Get-ChildItem $certPath -ErrorAction SilentlyContinue |
        Where-Object { $_.Subject -eq $CERT_SUBJECT } |
        ForEach-Object {
            Remove-Item $_.PSPath -Force
            Write-OK "Removed certificate from LocalMachine\$storeName"
        }
}

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 5 - Disable Test Signing
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Disabling Test Signing mode…"
& bcdedit /set testsigning off | Out-Null
Write-OK "Test signing disabled."

# ─────────────────────────────────────────────────────────────────────────────
#  DONE
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  Uninstallation complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Warn "Reboot required to fully remove the drivers."
Write-Host ""
$reboot = Read-Host "  Reboot now? (yes/no)"
if ($reboot.ToLower() -in @('yes','y')) { Restart-Computer -Force }
