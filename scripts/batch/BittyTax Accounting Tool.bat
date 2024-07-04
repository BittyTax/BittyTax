:: BittyTax Accounting Tool
::
:: This script lets you drag & drop a BittyTax records file (.xlsx) to be processed by the Accounting Tool.
::
:: --format PDF             BittyTax tax report in PDF format
:: --format IRS             IRS Form 8949 PDF(s)
:: --format TURBOTAX_CSV    TurboTax Online "Other (Gain/Loss)" CSV format
:: --format TURBOTAX_TXF    TurboTax Desktop TXF format
:: --format TAXACT          TaxAct "1099-B CSV import" format
::
@IF [%1] == [] (
   exit /b 1 | echo ERROR: No file specified
) ELSE (
   bittytax %1 --format PDF
)
@pause
