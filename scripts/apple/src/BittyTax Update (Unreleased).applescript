(*
   BittyTax Update (Unreleased)
   
   This script installs the latest "unreleased" version of BittyTax* from GitHub, see https://github.com/BittyTax/BittyTax.
   * You must have previously installed the official release.
   
   (c) Nano Nano Ltd 2024
*)

set theCommand to "pip install --force-reinstall --no-deps https://github.com/BittyTax/BittyTax/archive/refs/heads/master.zip"
set closeShell to "echo Press Return to continue . . .; read key; exit 0"
tell application "Terminal"
	do script theCommand & "; " & closeShell
	activate
end tell