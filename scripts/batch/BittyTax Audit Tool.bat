:: BittyTax Audit Tool
::
:: This script lets you drag & drop a BittyTax records file (.xlsx) to be processed by the Audit Tool.
::
@IF [%1] == [] (
   exit /b 1 | echo ERROR: No file specified
) ELSE (
   bittytax %1 --audit
)
@pause