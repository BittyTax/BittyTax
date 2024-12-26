(*
  BittyTax Install (Latest Release)
  
  This script installs (or upgrades) to the latest official release of BittyTax as stored on the Python Package Index (PyPI), see https://pypi.org/project/BittyTax/.
  
  (c) Nano Nano Ltd 2024
*)

set theCommand to "pip install BittyTax --upgrade"
set closeShell to "echo Press Return to continue . . .; read key; exit 0"
tell application "Terminal"
	do script theCommand & "; " & closeShell
	activate
end tell