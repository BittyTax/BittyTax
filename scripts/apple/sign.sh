#!/bin/bash
/usr/bin/codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Accounting Tool.app" -v
/usr/bin/codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Conversion Tool.app" -v
/usr/bin/codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Update (Unreleased).app" -v
/usr/bin/codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Config.app" -v
/usr/bin/codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Install (Latest Release).app" -v
