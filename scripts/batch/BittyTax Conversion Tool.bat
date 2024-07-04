:: BittyTax Conversion Tool
::
:: This script lets you drag & drop file(s) or folder(s) to be processed by the BittyTax Conversion Tool.
::
@IF [%1] == [] (
   exit /b 1 | echo ERROR: No file^(s^) specified
) ELSE (
   bittytax_conv %*
)
@pause