[app]

# (str) Title of your application
title = AI Chat Client

# (str) Package name
package.name = aichatclient

# (str) Package domain (needed for android/ios packaging)
package.domain = org.aichat

# (str) Application versioning
version = 1.0.1

# (str) Source code where the main.py live
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,ttf,json

# (list) Application requirements
requirements = python3,kivy==2.3.0,openssl,certifi,pyjnius,android

# (str) Presplash of the application
presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/data/icon.png

# (str) Supported orientation (one of landscape, sensorLandscape, portrait, sensorPortrait, all)
orientation = portrait

# (bool) Indicate if the application should be fullscreen or not
fullscreen = 1

# (string) Presplash background color (for android toolchain)
android.presplash_color = #080a0f

# (string) Presplash animation using Lottie format. Optional.
# android.presplash_lottie = "data/presplash.json"

# (list) Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE

# (int) Target Android API, should be as high as possible.
android.api = 33

# (int) Minimum API your APK / AAB will support.
android.minapi = 24

# (int) Android NDK API to use. This is the minimum API your app will support.
android.ndk_api = 24

# (bool) If True, then automatically accept SDK license
android.accept_sdk_license = True

# (list) The Android archs to build for
android.archs = arm64-v8a

# (bool) enables Android auto backup feature (Android API >=23)
android.allow_backup = True

# (str) Android logcat filters to use
android.logcat_filters = *:S python:D

# (bool) Copy library instead of making a libpymodules.so
android.copy_libs = 1

# (str) Android app theme — fullscreen, no title bar, no action bar
android.apptheme = "@android:style/Theme.NoTitleBar.Fullscreen"

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1
