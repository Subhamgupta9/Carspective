$destDir = "C:\Users\Divyanshi Gupta\AppData\Local\Programs"
$zipPath = Join-Path $destDir "node.zip"
$nodeDir = Join-Path $destDir "nodejs"

Write-Host "Downloading Node.js v20.18.0..."
curl.exe -L -o $zipPath https://nodejs.org/dist/v20.18.0/node-v20.18.0-win-x64.zip

Write-Host "Extracting Node.js..."
Expand-Archive -Path $zipPath -DestinationPath $destDir -Force
Remove-Item $zipPath -Force

if (Test-Path $nodeDir) {
    Remove-Item $nodeDir -Recurse -Force
}
Rename-Item (Join-Path $destDir "node-v20.18.0-win-x64") $nodeDir

# Check version
& (Join-Path $nodeDir "node.exe") -v
& (Join-Path $nodeDir "npm.cmd") -v

# Add to user PATH permanently
$userPath = [Environment]::GetEnvironmentVariable("Path", "User")
if ($userPath -notlike "*$nodeDir*") {
    [Environment]::SetEnvironmentVariable("Path", "$nodeDir;$userPath", "User")
}
$env:Path = "$nodeDir;$env:Path"
Write-Host "Node.js setup complete!"
