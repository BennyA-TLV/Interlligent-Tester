param(
    [Parameter(Mandatory=$true)]
    [string]$OutputPath,

    [string]$WindowTitle = "",

    [switch]$FullScreen
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;

public class CaptureWindowApi
{
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT
    {
        public int Left;
        public int Top;
        public int Right;
        public int Bottom;
    }

    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(
        IntPtr hWnd,
        out RECT rect
    );

    [DllImport("user32.dll")]
    public static extern IntPtr GetForegroundWindow();
}
"@

$bitmap = $null
$graphics = $null

Start-Sleep -Seconds 2

try {

    if ($FullScreen) {

        Write-Output "SCREENSHOT_MODE=FULL_SCREEN"

        $bounds = [System.Windows.Forms.SystemInformation]::VirtualScreen

        $x = $bounds.X
        $y = $bounds.Y
        $width = $bounds.Width
        $height = $bounds.Height

    }
    else {

        Write-Output "SCREENSHOT_MODE=WINDOW"
        Write-Output "WINDOW_TITLE=$WindowTitle"

        $wshell = New-Object -ComObject WScript.Shell

        if (-not $wshell.AppActivate($WindowTitle)) {
            throw "Window not found: $WindowTitle"
        }

        Start-Sleep -Milliseconds 500

        $handle = [CaptureWindowApi]::GetForegroundWindow()

        $rect = New-Object CaptureWindowApi+RECT

        if (-not [CaptureWindowApi]::GetWindowRect(
            $handle, [ref]$rect
        )) {
            throw "Failed to get window rectangle"
        }

        $x = $rect.Left
        $y = $rect.Top
        $width = $rect.Right - $rect.Left
        $height = $rect.Bottom - $rect.Top
    }

    if ($width -le 0 -or $height -le 0) {
        throw "Invalid screenshot dimensions"
    }

    Write-Output "WIDTH=$width"
    Write-Output "HEIGHT=$height"

    $bitmap = New-Object System.Drawing.Bitmap(
        $width,
        $height
    )

    $graphics = [System.Drawing.Graphics]::FromImage(
        $bitmap
    )

    $graphics.CopyFromScreen(
        $x,
        $y,
        0,
        0,
        $bitmap.Size
    )

    $bitmap.Save(
        $OutputPath,
        [System.Drawing.Imaging.ImageFormat]::Png
    )

    Write-Output "OUTPUT_PATH=$OutputPath"
    Write-Output "SCREENSHOT_SUCCESS"

    exit 0
}
catch {

    Write-Output "SCREENSHOT_ERROR: $_"

    exit 20
}
finally {

    if ($graphics) {
        $graphics.Dispose()
    }

    if ($bitmap) {
        $bitmap.Dispose()
    }
}