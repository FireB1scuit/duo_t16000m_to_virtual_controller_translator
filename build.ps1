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

pyinstaller --onefile --noconsole --name "HOSAS Translator" --clean gui.py

Write-Host ""
Write-Host "Built: dist\HOSAS Translator.exe"
