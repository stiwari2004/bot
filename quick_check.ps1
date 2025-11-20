# Quick file line counter - simple and fast
$path = $args[0]
if (-not $path) { 
    Write-Host "Usage: .\quick_check.ps1 <file_or_directory>"
    exit 1
}

if (Test-Path $path) {
    if ((Get-Item $path).PSIsContainer) {
        Get-ChildItem -Path $path -Filter "*.py" -Recurse -ErrorAction SilentlyContinue | 
            Where-Object { $_.FullName -notmatch '(pycache|\.git|node_modules)' } |
            ForEach-Object {
                try {
                    $content = [System.IO.File]::ReadAllLines($_.FullName)
                    $relPath = $_.FullName.Replace("$PWD\", "")
                    Write-Host "$relPath : $($content.Length) lines"
                } catch {
                    Write-Host "$($_.Name) : Error reading file"
                }
            }
    } else {
        try {
            $content = [System.IO.File]::ReadAllLines($path)
            Write-Host "$(Split-Path $path -Leaf) : $($content.Length) lines"
        } catch {
            Write-Host "Error reading file"
        }
    }
} else {
    Write-Host "Path not found: $path"
}



