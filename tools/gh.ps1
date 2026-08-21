# Thin wrapper so `gh` works before PATH refresh after install.
& "C:\Program Files\GitHub CLI\gh.exe" @args
exit $LASTEXITCODE