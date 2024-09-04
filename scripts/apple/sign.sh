#!/bin/bash

cp img/droplet.icns "BittyTax Accounting Tool.app/Contents/Resources/droplet.icns"
codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Accounting Tool.app" -v --options=runtime
zip -FSr "BittyTax Accounting Tool.zip" "BittyTax Accounting Tool.app"
xcrun notarytool submit "BittyTax Accounting Tool.zip" --keychain-profile "notarytool-password" --wait
xcrun stapler staple "BittyTax Accounting Tool.app"

cp img/droplet.icns "BittyTax Conversion Tool.app/Contents/Resources/droplet.icns"
codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Conversion Tool.app" -v --options=runtime
zip -FSr "BittyTax Conversion Tool.zip" "BittyTax Conversion Tool.app"
xcrun notarytool submit "BittyTax Conversion Tool.zip" --keychain-profile "notarytool-password" --wait
xcrun stapler staple "BittyTax Conversion Tool.app"

cp img/applet.icns "BittyTax Config.app/Contents/Resources/applet.icns"
codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Config.app" -v --options=runtime
zip -FSr "BittyTax Config.zip" "BittyTax Config.app"
xcrun notarytool submit "BittyTax Config.zip" --keychain-profile "notarytool-password" --wait
xcrun stapler staple "BittyTax Config.app"

cp img/applet.icns "BittyTax Update (Unreleased).app/Contents/Resources/applet.icns"
codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Update (Unreleased).app" -v --options=runtime
zip -FSr "BittyTax Update (Unreleased).zip" "BittyTax Update (Unreleased).app"
xcrun notarytool submit "BittyTax Update (Unreleased).zip" --keychain-profile "notarytool-password" --wait
xcrun stapler staple "BittyTax Update (Unreleased).app"

cp img/applet.icns "BittyTax Install (Latest Release).app/Contents/Resources/applet.icns"
codesign --force --sign "Developer ID Application: Scott Green (987HPREY9R)" "BittyTax Install (Latest Release).app" -v --options=runtime
zip -FSr "BittyTax Install (Latest Release).zip" "BittyTax Install (Latest Release).app"
xcrun notarytool submit "BittyTax Install (Latest Release).zip" --keychain-profile "notarytool-password" --wait
xcrun stapler staple "BittyTax Install (Latest Release).app"
