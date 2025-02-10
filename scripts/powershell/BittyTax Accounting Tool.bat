:: BittyTax Accounting Tool
::
:: This script lets you drag & drop a BittyTax records file (.xlsx) to be processed by the Accounting Tool.
::
@echo off
set PSScript=%~dpn0.ps1
powershell.exe -ExecutionPolicy Bypass -File "%PSScript%" %*