$taskName = "BrightAIBot"
schtasks /end /tn $taskName 2>$null
schtasks /delete /tn $taskName /f 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ Auto-start removed" -ForegroundColor Green
} else {
    Write-Host "✗ Failed or task not found" -ForegroundColor Red
}
