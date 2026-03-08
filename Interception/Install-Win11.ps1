#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Installs the Interception keyboard/mouse filter driver on Windows 11.

.DESCRIPTION
    The original Interception installer is incompatible with Windows 11 because
    the embedded .sys files are signed with a SHA-1 cross-certificate that
    Microsoft stopped honouring for kernel-mode drivers.

    This script:
      1. Checks prerequisites (64-bit OS, Admin, Secure Boot status)
      2. Creates a self-signed test code-signing certificate
      3. Re-signs keyboard.sys and mouse.sys with SHA-256 + that certificate
      4. Enables Windows Test Signing mode (bcdedit)
      5. Copies the drivers to %SystemRoot%\System32\Drivers\
      6. Registers the kernel services via sc.exe
      7. Appends 'keyboard' / 'mouse' to the relevant class UpperFilters
      8. Prompts for a reboot

.NOTES
    SECURE BOOT WARNING
    ───────────────────
    Test-signed drivers cannot load if Secure Boot is enabled in your BIOS/UEFI
    firmware.  If Secure Boot is ON you must disable it in your BIOS settings
    BEFORE rebooting after running this script.

    Check current status:  Confirm-SecureBootUEFI

    WHAT 'TEST SIGNING' DOES
    ────────────────────────
    Enabling test signing adds a visible "Test Mode" watermark to the Windows
    desktop.  This is expected behaviour and does not harm the system.
    The Uninstall-Win11.ps1 script disables test signing again.

    COMPATIBILITY
    ─────────────
    Tested on: Windows 11 22H2 / 23H2 / 24H2 (x64)
    Requires:  PowerShell 5.1+, Administrator rights, Reboot after install.
#>

[CmdletBinding(SupportsShouldProcess)]
param(
    [switch]$SkipSecureBootCheck,
    [switch]$Force
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

$DRIVER_DIR   = Join-Path $PSScriptRoot "driver"
$KBD_SYS      = Join-Path $DRIVER_DIR "keyboard.sys"
$MOUSE_SYS    = Join-Path $DRIVER_DIR "mouse.sys"
$SYSTEM_DRV   = "$env:SystemRoot\System32\drivers"
$CERT_SUBJECT = "CN=Interception Driver Test Cert, O=LocalDev, OU=GameBot"
$CERT_STORE   = "Cert:\LocalMachine\My"

$KBD_CLASS_GUID   = "{4D36E96B-E325-11CE-BFC1-08002BE10318}"
$MOUSE_CLASS_GUID = "{4D36E96F-E325-11CE-BFC1-08002BF6382B}"

# ─────────────────────────────────────────────────────────────────────────────
function Write-Header {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  Interception Driver Installer — Windows 11 Edition"           -ForegroundColor Cyan
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host ""
}

function Write-Step([string]$msg) {
    Write-Host "  ► $msg" -ForegroundColor Yellow
}

function Write-OK([string]$msg) {
    Write-Host "  ✓ $msg" -ForegroundColor Green
}

function Write-Warn([string]$msg) {
    Write-Host "  ⚠ $msg" -ForegroundColor Magenta
}

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 0 — Prerequisites
# ─────────────────────────────────────────────────────────────────────────────
Write-Header

Write-Step "Checking prerequisites…"

# 64-bit OS
if (-not [Environment]::Is64BitOperatingSystem) {
    throw "This installer only supports 64-bit (x64) Windows."
}
Write-OK "64-bit OS detected."

# Driver files present
foreach ($f in $KBD_SYS, $MOUSE_SYS) {
    if (-not (Test-Path $f)) {
        throw "Driver file not found: $f`nRe-clone the repository."
    }
}
Write-OK "Driver files found."

# Secure Boot check
$secureBoot = $false
try {
    $secureBoot = Confirm-SecureBootUEFI -ErrorAction Stop
} catch {
    # Confirm-SecureBootUEFI throws on non-UEFI systems — treat as Secure Boot OFF
    $secureBoot = $false
}

if ($secureBoot -and -not $SkipSecureBootCheck) {
    Write-Warn "Secure Boot is ENABLED in your BIOS/UEFI."
    Write-Warn "Test-signed drivers will NOT load while Secure Boot is ON."
    Write-Warn ""
    Write-Warn "You MUST disable Secure Boot in your BIOS settings before rebooting."
    Write-Warn "To bypass this check: run with -SkipSecureBootCheck"
    Write-Warn ""
    $answer = Read-Host "  Continue anyway? (yes/no)"
    if ($answer.ToLower() -notin @('yes','y')) {
        Write-Host "  Aborted." -ForegroundColor Red
        exit 1
    }
} elseif (-not $secureBoot) {
    Write-OK "Secure Boot is OFF — test-signed drivers will be accepted."
}

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 1 — Create / reuse a self-signed test code-signing certificate
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Creating self-signed test certificate…"

# Remove any stale certs with the same subject from all stores
foreach ($store in @("Root","TrustedPublisher","My")) {
    $s = "Cert:\LocalMachine\$store"
    Get-ChildItem $s -ErrorAction SilentlyContinue |
        Where-Object { $_.Subject -eq $CERT_SUBJECT } |
        Remove-Item -Force -ErrorAction SilentlyContinue
}

$cert = New-SelfSignedCertificate `
    -Subject         $CERT_SUBJECT `
    -Type            CodeSigningCert `
    -KeyUsage        DigitalSignature `
    -KeyAlgorithm    RSA `
    -KeyLength       2048 `
    -HashAlgorithm   SHA256 `
    -CertStoreLocation $CERT_STORE `
    -NotAfter        (Get-Date).AddYears(10) `
    -FriendlyName    "Interception Driver Test Cert"

Write-OK "Certificate created: $($cert.Thumbprint)"

# Trust the cert in LocalMachine\Root and LocalMachine\TrustedPublisher
foreach ($storeName in @('Root','TrustedPublisher')) {
    $store = [System.Security.Cryptography.X509Certificates.X509Store]::new(
        $storeName,
        [System.Security.Cryptography.X509Certificates.StoreLocation]::LocalMachine
    )
    $store.Open([System.Security.Cryptography.X509Certificates.OpenFlags]::ReadWrite)
    $store.Add($cert)
    $store.Close()
    Write-OK "Certificate added to LocalMachine\$storeName store."
}

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 2 — Sign the .sys files with SHA-256 Authenticode
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Re-signing keyboard.sys and mouse.sys with test certificate…"

# Work on copies in a temp dir so the originals stay intact
$tmpDir = Join-Path $env:TEMP "interception_install"
if (Test-Path $tmpDir) { Remove-Item $tmpDir -Recurse -Force }
New-Item -ItemType Directory -Path $tmpDir | Out-Null

$tmpKbd   = Join-Path $tmpDir "keyboard.sys"
$tmpMouse = Join-Path $tmpDir "mouse.sys"
Copy-Item $KBD_SYS   $tmpKbd
Copy-Item $MOUSE_SYS $tmpMouse

foreach ($sysFile in $tmpKbd, $tmpMouse) {
    $sigResult = Set-AuthenticodeSignature `
        -FilePath      $sysFile `
        -Certificate   $cert `
        -HashAlgorithm SHA256 `
        -TimestampServer "http://timestamp.digicert.com"

    if ($sigResult.Status -ne "Valid") {
        # Timestamp server may be unreachable — retry without timestamp
        Write-Warn "Timestamp server unavailable — signing without timestamp."
        $sigResult = Set-AuthenticodeSignature `
            -FilePath      $sysFile `
            -Certificate   $cert `
            -HashAlgorithm SHA256
    }

    if ($sigResult.Status -notin @("Valid","UnknownError")) {
        throw "Signing failed for $sysFile — Status: $($sigResult.Status)"
    }
    Write-OK "Signed: $(Split-Path $sysFile -Leaf)"
}

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 3 — Enable Test Signing mode
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Enabling Windows Test Signing mode…"
& bcdedit /set testsigning on | Out-Null
if ($LASTEXITCODE -ne 0) { throw "bcdedit failed — are you running as Administrator?" }
Write-OK "Test signing enabled. (A 'Test Mode' watermark will appear after reboot.)"

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 4 — Copy signed drivers to System32\Drivers
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Installing drivers to $SYSTEM_DRV …"

Copy-Item $tmpKbd   (Join-Path $SYSTEM_DRV "keyboard.sys") -Force
Copy-Item $tmpMouse (Join-Path $SYSTEM_DRV "mouse.sys")    -Force
Write-OK "Driver files copied to $SYSTEM_DRV"

Remove-Item $tmpDir -Recurse -Force

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 5 — Register kernel services via sc.exe
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Registering kernel services…"

foreach ($svc in @(
    @{ Name="keyboard"; Bin="\SystemRoot\System32\drivers\keyboard.sys"; Desc="Interception Keyboard Filter"; Group="Keyboard Port" },
    @{ Name="mouse";    Bin="\SystemRoot\System32\drivers\mouse.sys";    Desc="Interception Mouse Filter";    Group="Pointer Port"  }
)) {
    # Delete existing service if present
    $existing = Get-Service -Name $svc.Name -ErrorAction SilentlyContinue
    if ($existing) {
        & sc.exe stop  $svc.Name 2>&1 | Out-Null
        & sc.exe delete $svc.Name | Out-Null
        Start-Sleep -Milliseconds 500
        Write-Warn "Removed existing service: $($svc.Name)"
    }

    # create: type=kernel  start=boot  error=normal
    $result = & sc.exe create $svc.Name `
        type=  kernel `
        start= boot `
        error= normal `
        binpath= $svc.Bin `
        displayname= $svc.Desc `
        group= $svc.Group

    if ($LASTEXITCODE -ne 0) {
        throw "sc.exe create failed for '$($svc.Name)': $result"
    }
    Write-OK "Service registered: $($svc.Name)"
}

# ─────────────────────────────────────────────────────────────────────────────
#  STEP 6 — Add UpperFilters registry entries
# ─────────────────────────────────────────────────────────────────────────────
Write-Step "Configuring UpperFilters registry entries…"

function Add-UpperFilter {
    param([string]$ClassGuid, [string]$FilterName)

    $regPath = "HKLM:\SYSTEM\CurrentControlSet\Control\Class\$ClassGuid"

    if (-not (Test-Path $regPath)) {
        throw "Device class registry key not found: $regPath"
    }

    $current = (Get-ItemProperty -Path $regPath -Name UpperFilters -ErrorAction SilentlyContinue).UpperFilters
    if ($null -eq $current) { $current = @() }

    if ($FilterName -in $current) {
        Write-OK "UpperFilters[$ClassGuid] already contains '$FilterName' — skipping."
        return
    }

    $newVal = $current + $FilterName
    Set-ItemProperty -Path $regPath -Name UpperFilters -Value $newVal -Type MultiString
    Write-OK "Added '$FilterName' to UpperFilters [$ClassGuid]"
}

Add-UpperFilter -ClassGuid $KBD_CLASS_GUID   -FilterName "keyboard"
Add-UpperFilter -ClassGuid $MOUSE_CLASS_GUID -FilterName "mouse"

# ─────────────────────────────────────────────────────────────────────────────
#  DONE
# ─────────────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host "  Installation complete!" -ForegroundColor Green
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Green
Write-Host ""
Write-Warn "IMPORTANT: Reboot required for the driver to take effect."
if ($secureBoot) {
    Write-Warn "Remember to DISABLE Secure Boot in BIOS before rebooting!"
}
Write-Host ""
$reboot = Read-Host "  Reboot now? (yes/no)"
if ($reboot.ToLower() -in @('yes','y')) {
    Restart-Computer -Force
}
