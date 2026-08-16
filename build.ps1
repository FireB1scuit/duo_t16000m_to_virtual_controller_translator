# Builds a standalone Windows .exe for the HOSAS Translator GUI.
#
# Usage:
#   pip install -r requirements-dev.txt
#   .\build.ps1
#
# Output: dist\HOSAS Translator.exe - a single file, no console window,
# runnable on any Windows 11 machine that has the ViGEmBus driver installed
# (see README.md). Python itself does not need to be installed on the
# target machine; PyInstaller bundles the interpreter and dependencies.
#
# vgamepad loads ViGEmClient.dll from a path relative to its own package
# folder at runtime (not via a normal Python import), so PyInstaller's
# static analysis never finds it on its own - it has to be added explicitly
# as data, landing at the same "vgamepad\win\..." path inside the frozen
# bundle that vgamepad expects to find it at.

$vgamepadWinDir = python -c "import vgamepad, os; print(os.path.join(os.path.dirname(vgamepad.__file__), 'win'))"
if (-not $vgamepadWinDir) {
    Write-Error "Could not locate the vgamepad package - is it installed? (pip install -r requirements-dev.txt)"
    exit 1
}

pyinstaller --onefile --noconsole --name "HOSAS Translator" --clean `
    --add-data "$vgamepadWinDir;vgamepad\win" `
    gui.py

Write-Host ""
Write-Host "Built: dist\HOSAS Translator.exe"
