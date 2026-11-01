Write-Host ""
Write-Host "------------- NOTE -------------"
Write-Host "azd provision and azd up are not allowed for this project."
Write-Host "Infrastructure is owned by https://github.com/Azure/AI-Landing-Zones."
Write-Host "After deploying infrastructure, run azd env refresh with the same environment name, subscription and location."
Write-Host "Then run azd deploy"

exit 1