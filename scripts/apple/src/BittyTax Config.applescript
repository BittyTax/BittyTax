(*
   BittyTax Config
     
   This script lets you edit your BittyTax config file (bittytax.conf).
   
   (c) Nano Nano Ltd 2024
*)

try
	set theConfigFile to alias ((path to home folder as text) & ".bittytax:bittytax.conf")
on error
	display dialog "BittyTax config file does not exist" with icon stop
	return
end try
tell application "TextEdit"
	open theConfigFile
	activate
end tell