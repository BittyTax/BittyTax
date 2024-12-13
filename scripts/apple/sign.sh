#!/bin/bash

xattr -rc "BittyTax Accounting Tool.app"
cp img/droplet.icns "BittyTax Accounting Tool.app/Contents/Resources/droplet.icns"
codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Accounting Tool.app" -v --options=runtime

xattr -rc "BittyTax Conversion Tool.app"
cp img/droplet.icns "BittyTax Conversion Tool.app/Contents/Resources/droplet.icns"
codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Conversion Tool.app" -v --options=runtime

xattr -rc "BittyTax Config.app"
cp img/applet.icns "BittyTax Config.app/Contents/Resources/applet.icns"
codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Config.app" -v --options=runtime

xattr -rc "BittyTax Update (Unreleased).app"
cp img/applet.icns "BittyTax Update (Unreleased).app/Contents/Resources/applet.icns"
codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Update (Unreleased).app" -v --options=runtime

xattr -rc "BittyTax Install (Latest Release).app"
cp img/applet.icns "BittyTax Install (Latest Release).app/Contents/Resources/applet.icns"
codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Install (Latest Release).app" -v --options=runtime
