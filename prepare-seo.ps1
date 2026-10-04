# Local counterpart of the GitHub Pages workflow. Requires Python 3.10+, no packages.
# Generated files go to _site; the editable site source is left intact.
[CmdletBinding()]
param(
    [string]$SiteUrl = '',
    [string]$Python = ''
)
$ErrorActionPreference = 'Stop'
$scriptFile = Join-Path $PSScriptRoot 'scripts/build_site.py'
$pythonArguments = @()
if ($Python) {
    $pythonCommand = $Python
} elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $pythonCommand = 'py'
    $pythonArguments += '-3'
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $pythonCommand = 'python'
} else {
    throw 'Python 3.10+ is required locally. GitHub Actions needs no local installation.'
}
$pythonArguments += $scriptFile
if ($SiteUrl) { $pythonArguments += @('--site-url', $SiteUrl) }
& $pythonCommand @pythonArguments
if ($LASTEXITCODE -ne 0) { throw 'Static site preparation failed. Check the message above.' }
