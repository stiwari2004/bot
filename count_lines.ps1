# Simple PowerShell script to count lines - won't hang
param(
    [Parameter(Mandatory=$true)]
    [string]$Path
)

if (Test-Path $Path) {
    if (Test-Path $Path -PathType Container) {
        # Directory
        Get-ChildItem -Path $Path -Filter "*.py" -Recurse | Where-Object { 
            $_.FullName -notmatch '(__pycache__|\.git|node_modules)' 
        } | ForEach-Object {
            $lines = (Get-Content $_.FullName -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
            $relPath = $_.FullName.Replace((Resolve-Path $Path).Path + "\", "")
            Write-Output "$relPath : $lines lines"
        }
    } else {
        # File
        $lines = (Get-Content $Path -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
        Write-Output "$(Split-Path $Path -Leaf) : $lines lines"
    }
} else {
    Write-Output "Path not found: $Path"
}

