#!/bin/bash

zip -FSr "BittyTax Accounting Tool.zip" "BittyTax Accounting Tool.app"
xcrun notarytool submit "BittyTax Accounting Tool.zip" --keychain-profile "notarytool-password" --wait
xcrun stapler staple "BittyTax Accounting Tool.app"

zip -FSr "BittyTax Conversion Tool.zip" "BittyTax Conversion Tool.app"
xcrun notarytool submit "BittyTax Conversion Tool.zip" --keychain-profile "notarytool-password" --wait
xcrun stapler staple "BittyTax Conversion Tool.app"

zip -FSr "BittyTax Config.zip" "BittyTax Config.app"
xcrun notarytool submit "BittyTax Config.zip" --keychain-profile "notarytool-password" --wait
xcrun stapler staple "BittyTax Config.app"

zip -FSr "BittyTax Update (Unreleased).zip" "BittyTax Update (Unreleased).app"
xcrun notarytool submit "BittyTax Update (Unreleased).zip" --keychain-profile "notarytool-password" --wait
xcrun stapler staple "BittyTax Update (Unreleased).app"

zip -FSr "BittyTax Install (Latest Release).zip" "BittyTax Install (Latest Release).app"
xcrun notarytool submit "BittyTax Install (Latest Release).zip" --keychain-profile "notarytool-password" --wait
xcrun stapler staple "BittyTax Install (Latest Release).app"
