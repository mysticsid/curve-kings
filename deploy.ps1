# Publishes Curve Kings to https://mysticsid.github.io/curve-kings/
# Run from this folder:   powershell -ExecutionPolicy Bypass -File deploy.ps1
# The first time, Git opens a GitHub sign-in window: approve it once.
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot
$git = Join-Path $root 'Git\cmd\git.exe'
$repo = 'https://github.com/mysticsid/curve-kings.git'
Set-Location $root

Write-Host '1/3  Saving and uploading the source (main branch)...'
& $git add -A
& $git commit -q -m "Update $(Get-Date -Format 'yyyy-MM-dd HH:mm')" 2>$null
if (-not (& $git remote)) { & $git remote add origin $repo }
& $git push -u origin main

Write-Host '2/3  Packaging the app...'
node tools\build_web.js

Write-Host '3/3  Publishing the app (gh-pages branch)...'
Set-Location (Join-Path $root 'dist')
& $git init -q -b gh-pages
& $git add -A
& $git -c user.name="Curve Kings" -c user.email="deploy@curve-kings" commit -q -m "Deploy $(Get-Date -Format 'yyyy-MM-dd HH:mm')"
& $git push -f $repo gh-pages
Remove-Item -Recurse -Force .git
Set-Location $root

Write-Host ''
Write-Host 'Done. Live in about a minute at: https://mysticsid.github.io/curve-kings/'
