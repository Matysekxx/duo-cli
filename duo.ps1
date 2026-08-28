param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$venvPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    & $venvPython "$PSScriptRoot\main.py" @Args
} else {
    & python "$PSScriptRoot\main.py" @Args
}
