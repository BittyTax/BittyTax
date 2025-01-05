:: BittyTax Conversion Tool
::
:: This script lets you drag & drop file(s) or folder(s) to be processed by the BittyTax Conversion Tool.
::
@echo off
set PSScript=%~dpn0.ps1
powershell.exe -File "%PSScript%" %*