$taskName = "BrightAIBot"
$scriptPath = "A:\trading agent\start_bot.vbs"
$wscript = "$env:SystemRoot\System32\wscript.exe"

schtasks /end /tn $taskName 2>$null
schtasks /delete /tn $taskName /f 2>$null

$cmd = "$wscript //B `"$scriptPath`""
schtasks /create /tn $taskName /tr $cmd /sc onstart /delay 0001:00 /ru $env:USERNAME /f

if ($LASTEXITCODE -eq 0) {
  Write-Host "OK: Auto-start installed (BrightAIBot runs 1 min after boot)"
} else {
  Write-Host "FAILED: Run as Administrator"
}
