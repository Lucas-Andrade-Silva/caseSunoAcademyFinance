# Gera web/openapi.json a partir da API e o cliente TypeScript a partir dele (ADR 0005).
# Precisa de rede uma vez, para baixar o pacote `openapi-typescript` via npx; nada disso
# entra no pytest, que roda inteiramente offline.
#
#   powershell -File scripts/gerar-cliente.ps1

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $PSScriptRoot

Push-Location $raiz
try {
    $env:PYTHONIOENCODING = "utf-8"  # acentos do schema (console do Windows abre em cp1252)

    Write-Host "Gerando web/openapi.json..."
    # Out-File -Encoding utf8 grava com BOM no Windows PowerShell 5.1; escreve sem BOM à mão,
    # porque um JSON com BOM quebra parser que não espera (openapi-typescript tolera, outros não).
    $schema = uv run python -m suno.api.openapi | Out-String
    [System.IO.File]::WriteAllText("$raiz\web\openapi.json", $schema.TrimEnd("`r", "`n") + "`n", (New-Object System.Text.UTF8Encoding $false))

    New-Item -ItemType Directory -Force -Path "web/src/api" | Out-Null

    Write-Host "Gerando web/src/api/schema.d.ts..."
    npx --yes openapi-typescript web/openapi.json -o web/src/api/schema.d.ts

    Write-Host "Cliente gerado."
}
finally {
    Pop-Location
}
