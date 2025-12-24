param(
    [Parameter(Position=0)][string]$Prompt = ""
)

$promptText = ($Prompt | Out-String).Trim()

# Username is optional for GitHub token auth; but Git may prompt for it.
# Use $env:GITHUB_USER if set; else default to x-access-token.
if ($promptText -match '(?i)username') {
    $user = ($env:GITHUB_USER ?? "").Trim()
    if (-not $user) { $user = "x-access-token" }
    Write-Output $user
    exit 0
}

# Password / token
$token = ((($env:GITHUB_PAT ?? "").Trim()) )
if (-not $token) { $token = ((($env:GITHUB_TOKEN ?? "").Trim())) }

if (-not $token) {
    # Keep output empty to avoid leaking anything; signal failure via exit code.
    Write-Error "Missing token. Set GITHUB_PAT (or GITHUB_TOKEN) in your environment."
    exit 1
}

Write-Output $token
exit 0
