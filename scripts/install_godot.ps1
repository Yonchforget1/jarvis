$godotDir = "C:\Godot"
$zipPath = "$godotDir\godot4.zip"
$url = "https://github.com/godotengine/godot/releases/download/4.3-stable/Godot_v4.3-stable_win64.exe.zip"

Write-Host "Creating Godot directory..."
New-Item -ItemType Directory -Force -Path $godotDir | Out-Null

# Remove corrupted file if exists
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }

Write-Host "Downloading Godot 4.3 stable using .NET WebClient..."
$wc = New-Object System.Net.WebClient
$wc.Headers.Add("User-Agent", "Mozilla/5.0")
try {
    # Need to follow GitHub redirects - use HttpWebRequest
    [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.SecurityProtocolType]::Tls12
    $wc.DownloadFile($url, $zipPath)
    Write-Host "Downloaded successfully. Size: $((Get-Item $zipPath).Length) bytes"
} catch {
    Write-Host "WebClient failed: $_"
    Write-Host "Trying curl..."
    curl.exe -L -o $zipPath $url
    Write-Host "curl download complete. Size: $((Get-Item $zipPath).Length) bytes"
}

Write-Host "Extracting..."
Expand-Archive -Path $zipPath -DestinationPath $godotDir -Force

Write-Host "Looking for Godot executable..."
Get-ChildItem $godotDir -Recurse -Filter "*.exe"

$exe = Get-ChildItem -Path $godotDir -Filter "Godot*.exe" -Recurse | Select-Object -First 1
if ($exe) {
    $newPath = Join-Path $godotDir "godot.exe"
    if (Test-Path $newPath) { Remove-Item $newPath }
    Copy-Item -Path $exe.FullName -Destination $newPath
    Write-Host "Godot installed at: $newPath"
} else {
    Write-Host "ERROR: No Godot exe found"
}

Remove-Item $zipPath -ErrorAction SilentlyContinue
Write-Host "Verifying..."
& "$godotDir\godot.exe" --version
