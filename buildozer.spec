[app]
title = NFC Scanner
package.name = nfcscanner
package.domain = org.yourname
source.dir = .
source.include_exts = py,png,jpg,kv,atlas
version = 0.1

requirements = python3,kivy,pyjnius

orientation = portrait
fullscreen = 0

android.permissions = NFC,INTERNET
android.api = 33
android.minapi = 21
android.ndk = 25b
android.archs = arm64-v8a,armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 0
