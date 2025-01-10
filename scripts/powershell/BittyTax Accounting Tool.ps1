<#
    BittyTax Accounting Tool

    This script lets you select a BittyTax transaction records file (.xlsx) to be processed by the Accounting Tool.

    (c) Nano Nano Ltd 2025
#>

param (
    [Parameter(ValueFromRemainingArguments = $true)]
    $droppedFiles
)

Add-Type -AssemblyName System.Windows.Forms
[System.Windows.Forms.Application]::EnableVisualStyles();

$iconBase64 = @'
iVBORw0KGgoAAAANSUhEUgAAACAAAAAgCAMAAABEpIrGAAACnVBMVEUAAAD4kxr3kxr1khr2lBzw8PCEhIRGRkZHR0dCQkL3lBr3lBr2lBo2NTM1NTX6kxf7lRj2kxlAQED2lBr1kxr4kxv5khv1kRrxjRwvLy/1lRX/oACBWipCQkL3kxr3kxr/mhRAQED3kxr3kxr3kxo6Ojo/Pz8yMjL3khoxMTH3kxr2khv2kxo5OTn4khr5kxr3kxr1kxsyMjL4lBr4khr/tQD5kRdFRUXzlxf3kxr///+kpKSlpaX3kxusrKz7lRr/ox2ioqH3khj/mBv+lxv/nhyop6b/nBuoqKiTk5P/oRze3t+ZmZlPUlX4kBL3iQOpqamenp6MjY1weYR5eXlxcnJsbGxYYGr/mBf+kgz/+vPs7Oyzs7Opq62hpKd8hpGQkJCIiIh8fHxrcXlTVVdHTldQT0//pDGEVRv/mhr4lBr9lBb/mxX4jQv2iwjj5OTe3NrZ2dn/79bT1NXHx8fCwsG5ubn/47atra3+1aSXl5aIjpR1fomDg4OAgIBwdnxtcnlgaXRlZWX5slxbW1tQUVH5q01CR01ISkxtW0VERERfUUD4ojj4nCyNYCucZyiIXSj3mCT/px2/dh36kxf3kRX/oRP/mRL/jQHq+P/g6/f//vTw8PDg5u7n5+fY1tTNzs/MzMy+w8n837y7vLz/57mztLaurq781qmYnqadoKT/26H9zpb/05X7zZWKi4t+g4r7xoX/y4R3e3/6wHqWiXncr3iIfnL/wGtmZmZRW2ZLVmQ8TmOReFpaWlo/S1o/Slj/uFS2h06Cak3al0XzokFmVkFhUj9yWDiIYjVfSjBQQjBjSiyeaiuEWyr8miK6dCCVYCD3lR7KfB3iiRz/oxr/qxjYfxP/lg//lg7mggn/lwXYdwH2gQDYcwD0gQVSAAAAOXRSTlMA+uhOG/7+4NzPvrKgmZRzXVFHRD83JiISDQwE+/Tw4uDc29rVz76+t62nopOQiICAaGBFRC0sGha8ueGSAAACe0lEQVQ4y72RZVfbYACF3+LutjF3d8ubpEmaNqGlLVKhBYa7M2y4uzNs7u7u7u4uv2Vv0vFhDL7t8Hx97rnnnnPBBBOwYfL40sbdyUqCSaY7e4wZCnCR0wqeZVleRUuW/+utJTSbgQlQpqzBTzPWjvIraYVoSe1Q5vvunlfdU1zd3FyXrh/xnjRLYiSWozXfvfc8ubYiNrZcGRcep587Mk/OkxgmI+tff71/42hBMCJ3V1RUVEHdQiCygEYey+6A8GbznvxiKYHjRGh0YZ5tvnG+4NcpKORRw5Xddw4UMQxOEATOhIUxhbbB+nmrAFhCWwb2m1urDx2LwRkmJiY0FEeZoh25SQ0AzOYxEfPD5BaNRtOYkqLRJJWJib3qW8XARiIXvSykdGve5x+/Lm3b+eDb2whhCaduUUuBj5wSA1pZJITnUlM3QZj6fUvERhSQVjVsJoAnS1kK6iFEEnEie+iNJWAwSnHgLTSQspCf++F2M38cwpLhL4N/GvR1qMGPRBsG3h05BeHFtLS0y+Wnn/Z0PauWCgFlCseBQKt0DMtpgoika7E6g8Gg0+nOcMgTQcrGhGgAFqmECZ0XIuG+NiL6sFSEwAmOCLe72hYPwGqaEjZgsPRgRbKS4YIEOIJg4iuNjl6OAIA5KvRFyFkoK4l8cft8uLJMrUZnxlfaGWdOAgK+KvT2QGdTLzw53NV8vTaxJjGxJiGhSj8VeZEVfRRJanNkHb2ZWR9ePnnc3v6o1cHB3t4LjODSJxcf15IZpixTZj//0R38zTIV+txCBmWi0z3AaLxn0ap0OUVRcp5WOPmDMbB2nsYqFArWarEvGIdAvzXWPv7gv/Mbf2bVmEONLrIAAAAASUVORK5CYII=
'@
$iconBytes = [Convert]::FromBase64String($iconBase64)
$iconStream = [System.IO.MemoryStream]::new($iconBytes, 0, $iconBytes.Length)

function Show-FileDialog {
    $openFileDialog = New-Object System.Windows.Forms.OpenFileDialog
    $openFileDialog.Title = 'Select a BittyTax transaction records spreadsheet:'
    $openFileDialog.Filter = 'Excel files (*.xlsx;*.xls)|*.xlsx;*.xls|CSV files (*.csv)|*.csv'
    $openFileDialog.ShowDialog((New-Object System.Windows.Forms.Form -Property @{
                TopMost       = $true
                StartPosition = 'CenterScreen'
                Icon          = [System.Drawing.Icon]::FromHandle(([System.Drawing.Bitmap]::new($iconStream).GetHIcon()))
            })) | Out-Null
    return $openFileDialog.FileNames
}

function Show-ArgumentInputBox {
    $form = New-Object Windows.Forms.Form
    $form.Text = 'BittyTax Accounting Tool'
    $form.Size = New-Object Drawing.Size(290, 140)
    $form.StartPosition = 'CenterScreen'
    $form.FormBorderStyle = "FixedDialog"
    $form.MinimizeBox = $false
    $form.MaximizeBox = $false
    $form.Icon = [System.Drawing.Icon]::FromHandle(([System.Drawing.Bitmap]::new($iconStream).GetHIcon()))
    $form.Topmost = $true
    $form.TopLevel = $true

    $label = New-Object Windows.Forms.Label
    $label.Location = New-Object Drawing.Point(10, 15)
    $label.Size = New-Object Drawing.Size(255, 25)
    $label.Text = "Add extra 'bittytax' command arguments?"
    $form.Controls.Add($label)

    $textBox = New-Object Windows.Forms.TextBox
    $textBox.Location = New-Object Drawing.Point(10, 40)
    $textBox.Size = New-Object Drawing.Size(255, 20)
    $textBox.MaxLength = 64
    $form.Controls.Add($textBox)

    $okButton = New-Object Windows.Forms.Button
    $okButton.Location = New-Object Drawing.Point(55, 70)
    $okButton.Text = 'OK'
    $okButton.DialogResult = [Windows.Forms.DialogResult]::OK
    $form.AcceptButton = $okButton
    $form.Controls.Add($okButton)

    $cancelButton = New-Object Windows.Forms.Button
    $cancelButton.Location = New-Object Drawing.Point(145, 70)
    $cancelButton.Text = 'Cancel'
    $cancelButton.DialogResult = [Windows.Forms.DialogResult]::Cancel
    $form.CancelButton = $cancelButton
    $form.Controls.Add($cancelButton)

    $form.Add_Shown({ $form.Activate() })
    $dialogResult = $form.ShowDialog()
    return @{
        ButtonPressed = $dialogResult
        Arguments     = $textBox.Text
    }
}

function Show-SuccessMessageBox {
    $form = New-Object Windows.Forms.Form
    $form.Text = 'BittyTax Accounting Tool'
    $form.Size = New-Object Drawing.Size(290, 130)
    $form.StartPosition = 'CenterScreen'
    $form.FormBorderStyle = 'FixedDialog'
    $form.MinimizeBox = $false
    $form.MaximizeBox = $false
    $form.Icon = [System.Drawing.Icon]::FromHandle(([System.Drawing.Bitmap]::new($iconStream).GetHIcon()))
    $form.Topmost = $true
    $form.TopLevel = $true
    
    $label = New-Object Windows.Forms.Label
    $label.Location = New-Object Drawing.Point(10, 15)
    $label.MaximumSize = New-Object Drawing.Size(255, 30)
    $label.Text = 'Report generated. Open Document or Show in Folder?'
    $label.AutoSize = $true

    $form.Controls.Add($label)
    
    $openButton = New-Object Windows.Forms.Button
    $openButton.Text = 'Open'
    $openButton.Location = New-Object Drawing.Point(10, 60)
    $openButton.Add_Click({ $form.Tag = "Open"; $form.Close() })
    $form.Controls.Add($openButton)
    
    $showButton = New-Object Windows.Forms.Button
    $showButton.Text = 'Show'
    $showButton.Location = New-Object Drawing.Point(100, 60)
    $showButton.Add_Click({ $form.Tag = "Show"; $form.Close() })
    $form.Controls.Add($showButton)
    
    $cancelButton = New-Object Windows.Forms.Button
    $cancelButton.Text = 'Cancel'
    $cancelButton.Location = New-Object Drawing.Point(190, 60)
    $cancelButton.Add_Click({ $form.Tag = "Cancel"; $form.Close() })
    $form.Controls.Add($cancelButton)
    
    $form.Add_Shown({ $form.Activate() })
    $form.ShowDialog()
    return $form.Tag
}

function Search-Success {
    param (
        [string]$line
    )
    
    $resultSuccessList = @("PDF report created: ", "EXCEL report created: ", "export file created: ")
    foreach ($resultSuccess in $resultSuccessList) {
        if ($line.StartsWith($resultSuccess)) {
            $filename = $line.Substring($resultSuccess.Length).Trim()
            return @{ Success = $true; Filename = $filename }
        }
    }
    return @{ Success = $false; Filename = $null }
}

function BittyTaxAccountingTool {
    $host.UI.RawUI.WindowTitle = 'BittyTax Accounting Tool'

    if (!$droppedFiles) {
        $files = Show-FileDialog
    }
    else {
        $files = $droppedFiles
    }

    if ($files.Count -eq 0) {
        return
    }

    $result = Show-ArgumentInputBox

    # Flush input buffer otherwise arguments can appear as input to BittyTax prompts
    $host.UI.RawUI.Flushinputbuffer() 

    if ($result.ButtonPressed -ne "OK") {
        return
    }

    $command = "bittytax"
    if ($result.Arguments -ne "") {
        $command += " " + $result.Arguments
    }

    # Prepare the list of files taking into consideration spaces in filenames
    $allFiles = ($files | ForEach-Object { "`"$_`"" }) -join " "
    $command += " " + $allFiles

    # Change directory so output file will be created in some folder as the input file
    $directory = Split-Path -Parent $files | Select-Object -First 1
    Set-Location -Path $directory

    Write-Host $command -ForegroundColor DarkGray

    # Ensure output is recognised as UTF-8
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8

    Invoke-Expression $command | Tee-Object -Variable output

    # Remove ANSI colour codes
    $output = $output | ForEach-Object { $_ -replace "\x1b\[\d+(;\d+)*m", "" }

    # Check for success message in the command output
    $success = $false
    $outputFilePath = ""
    foreach ($line in $output) {
        $result = Search-Success -line $line
        if ($result.Success) {
            $success = $true
            $outputFilePath = $result.Filename
            break
        }
    }

    if ($success) {
        $result = Show-SuccessMessageBox
        switch ($result) {
            "Open" {
                Start-Process -FilePath $outputFilePath
            }
            "Show" {
                Start-Process explorer.exe "/select,`"$outputFilePath`""
            }
        }
    }
    else {
        Write-Host 'Press Enter to continue...' -ForegroundColor White
        Read-Host
    }
}

BittyTaxAccountingTool