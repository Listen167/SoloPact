param(
    [string]$Version = "v0.1.0",
    [string]$TeamName = "solo-developer"
)

$ErrorActionPreference = "Stop"
$workspace = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$packageName = "ReceivablesRadar+$TeamName+$Version+$stamp"
$packageRoot = Join-Path $workspace "output\$packageName"

New-Item -ItemType Directory -Path $packageRoot -Force | Out-Null
foreach ($folder in @("ppt", "project", "video", "codearts_proof", "readme")) {
    New-Item -ItemType Directory -Path (Join-Path $packageRoot $folder) -Force | Out-Null
}

function Copy-CleanDirectory {
    param([string]$Source, [string]$Destination)
    $excludedNames = @("node_modules", "dist", "__pycache__", ".pytest_cache", ".ruff_cache", "storage", ".coverage")
    $excludedExtensions = @(".pyc", ".db")
    New-Item -ItemType Directory -Path $Destination -Force | Out-Null
    foreach ($item in Get-ChildItem -LiteralPath $Source -Force) {
        if (($excludedNames -contains $item.Name) -or ($excludedExtensions -contains $item.Extension)) {
            continue
        }
        $target = Join-Path $Destination $item.Name
        if ($item.PSIsContainer) {
            Copy-CleanDirectory -Source $item.FullName -Destination $target
        } else {
            Copy-Item -LiteralPath $item.FullName -Destination $target -Force
        }
    }
}

Copy-CleanDirectory -Source (Join-Path $workspace "backend") -Destination (Join-Path $packageRoot "project\backend")
Copy-CleanDirectory -Source (Join-Path $workspace "frontend") -Destination (Join-Path $packageRoot "project\frontend")
Copy-CleanDirectory -Source (Join-Path $workspace "demo") -Destination (Join-Path $packageRoot "project\demo")
Copy-CleanDirectory -Source (Join-Path $workspace "docs") -Destination (Join-Path $packageRoot "project\docs")
Copy-Item -Force (Join-Path $workspace "docker-compose.yml") (Join-Path $packageRoot "project")
Copy-Item -Force (Join-Path $workspace ".env.example") (Join-Path $packageRoot "project")
Copy-Item -Force (Join-Path $workspace "README.md") (Join-Path $packageRoot "project")

Copy-Item -Recurse -Force (Join-Path $workspace "ppt\*") (Join-Path $packageRoot "ppt")
Copy-Item -Recurse -Force (Join-Path $workspace "video\*") (Join-Path $packageRoot "video")
Copy-Item -Recurse -Force (Join-Path $workspace "codearts_proof\*") (Join-Path $packageRoot "codearts_proof")
Copy-Item -Recurse -Force (Join-Path $workspace "readme\*") (Join-Path $packageRoot "readme")

$zipPath = "$packageRoot.zip"
Compress-Archive -Path (Join-Path $packageRoot "*") -DestinationPath $zipPath
Write-Output "Submission package created: $zipPath"

