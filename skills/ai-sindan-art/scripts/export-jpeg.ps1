param(
    [Parameter(Mandatory=$true)][string]$AssetDirectory,
    [Parameter(Mandatory=$true)][string]$DeliveryDirectory
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing
$assetRoot = (Resolve-Path -LiteralPath $AssetDirectory).Path
$deliveryRoot = (Resolve-Path -LiteralPath $DeliveryDirectory).Path
if ($assetRoot -eq $deliveryRoot) { throw 'Originals and delivery images must use separate directories.' }
$encoder = [System.Drawing.Imaging.ImageCodecInfo]::GetImageEncoders() | Where-Object MimeType -eq 'image/jpeg'
$parameters = [System.Drawing.Imaging.EncoderParameters]::new(1)
$parameters.Param[0] = [System.Drawing.Imaging.EncoderParameter]::new([System.Drawing.Imaging.Encoder]::Quality, [long]82)
try {
    foreach ($source in Get-ChildItem -LiteralPath $assetRoot -Filter '*.png') {
        if ($source.BaseName -notmatch '^[SE][GD][BI][CT]$') { continue }
        $original = [System.Drawing.Image]::FromFile($source.FullName)
        $bitmap = $null
        $graphics = $null
        try {
            $scale = 512.0 / [Math]::Max($original.Width, $original.Height)
            if ($scale -gt 1) { $scale = 1.0 }
            $bitmap = [System.Drawing.Bitmap]::new([int]($original.Width*$scale), [int]($original.Height*$scale))
            $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
            $graphics.Clear([System.Drawing.Color]::FromArgb(247,244,235))
            $graphics.InterpolationMode = [System.Drawing.Drawing2D.InterpolationMode]::HighQualityBicubic
            $graphics.DrawImage($original, 0, 0, $bitmap.Width, $bitmap.Height)
            $bitmap.Save((Join-Path $deliveryRoot ($source.BaseName+'.jpg')), $encoder, $parameters)
        } finally {
            if ($graphics) { $graphics.Dispose() }
            if ($bitmap) { $bitmap.Dispose() }
            $original.Dispose()
        }
    }
} finally { $parameters.Dispose() }
