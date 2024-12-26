(* 
   BittyTax Conversion Tool
   
   This script lets you drag & drop file(s) or folder(s) to be processed by the BittyTax Conversion Tool
   
   (c) Nano Nano Ltd 2024
*)

on run
	(*
	This is a workaround to prevent having to grant access for every spreadsheet you want to open
	*)
	set sd to path to startup disk
	tell application id "com.microsoft.Excel" -- Microsoft Excel
		try
			close sd -- will error
		end try
	end tell
	
	choose file of type {"public.comma-separated-values-text", "public.plain-text", "org.openxmlformats.spreadsheetml.sheet", "com.microsoft.excel.xls"} with prompt "Select data file(s) for BittyTax to convert:" with multiple selections allowed
	open result
end run

on open droppedFiles
	set theCommand to "bittytax_conv"
	set closeShell to "echo Press Return to continue . . .; read key; exit 0"
	set theResponse to display dialog "Add extra \"bittytax_conv\" command arguments?" default answer "" with icon {path to resource "droplet.icns"} buttons {"Cancel", "OK"} default button "OK"
	set theArguments to text returned of theResponse
	if theArguments is not equal to "" then
		set theArguments to " " & theArguments
	end if
	set posixFiles to ""
	repeat with droppedFile in droppedFiles
		tell application "Finder" to set posixDirectory to quoted form of POSIX path of ((container of droppedFile) as text)
		set posixFiles to posixFiles & " " & quoted form of POSIX path of droppedFile
	end repeat
	tell application "Terminal"
		set newTab to do script "cd " & posixDirectory & "; " & theCommand & theArguments & posixFiles
		set windowId to first window's id of (every window whose tabs contains newTab)
		set current settings of newTab to settings set "Homebrew"
		activate
		delay 1 -- wait for script to start
		repeat while busy of newTab
			delay 0.2
		end repeat
		set commandHistory to the contents of window id windowId
		set allParas to paragraphs of commandHistory
		set success to false
		repeat with thisPara in allParas
			if thisPara begins with "output EXCEL file created: " then
				set success to true
				set tempTid to AppleScript's text item delimiters
				set AppleScript's text item delimiters to ": "
				set filename to item 2 of text items of thisPara as POSIX file
				set AppleScript's text item delimiters to tempTid
				exit repeat
			end if
		end repeat
		if success then
			try
				set theResponse to display dialog "Conversion successful. Open Spreadsheet or Show in Finder?" with icon note buttons {"Cancel", "Open", "Show"} default button "Open" giving up after 15
			on error
				do script closeShell in newTab
				return
			end try
			if gave up of theResponse then
				do script closeShell in newTab
				return
			end if
			tell application "Finder"
				if button returned of theResponse is "Open" then
					open filename as alias
				else
					reveal filename as alias
					activate
				end if
			end tell
			close window id windowId
		else
			do script closeShell in newTab
		end if
	end tell
end open
