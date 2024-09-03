#!/bin/bash
/usr/bin/codesign --verify "BittyTax Accounting Tool.app" -v
/usr/bin/codesign --verify "BittyTax Conversion Tool.app" -v
/usr/bin/codesign --verify "BittyTax Update (Unreleased).app" -v
/usr/bin/codesign --verify "BittyTax Config.app" -v
/usr/bin/codesign --verify "BittyTax Install (Latest Release).app" -v
