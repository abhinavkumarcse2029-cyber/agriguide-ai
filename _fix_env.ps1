# _fix_env.ps1 — Run this ONCE from the agriguide-ai directory to create a
# clean .env file.  Delete this script afterwards.
# Usage:  cd playground\agriguide-ai ; .\\_fix_env.ps1

$key = Read-Host -Prompt "Paste your IBM API key (will not be echoed)" -AsSecureString
$plain = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
    [Runtime.InteropServices.Marshal]::SecureStringToBSTR($key)
)

$content = @"
# IBM watsonx.ai Configuration
IBM_API_KEY=$plain
IBM_PROJECT_ID=32e7909c-6a65-4be4-b345-67e1273c330b
IBM_URL=https://us-south.ml.cloud.ibm.com
# Leave MODEL_NAME empty — the app will query watsonx and auto-select a model.
MODEL_NAME=

# Flask Configuration
FLASK_SECRET_KEY=agriguide-prod-secret-2024-xK9mP3qL
FLASK_ENV=development
FLASK_DEBUG=True

# Application Configuration
APP_NAME=AgriGuide AI
APP_VERSION=1.0.0
"@

Set-Content -Path ".env" -Value $content -Encoding UTF8 -NoNewline:$false
Write-Host ""
Write-Host ".env written successfully." -ForegroundColor Green
Write-Host "Verify (key hidden):"
Get-Content ".env" | ForEach-Object {
    if ($_ -match "^IBM_API_KEY=") { "IBM_API_KEY=<hidden>" } else { $_ }
}
