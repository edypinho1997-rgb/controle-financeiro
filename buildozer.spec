[app]
title = Controle Financeiro
package.name = controlefinanceiro
package.domain = org.edy

source.dir = .
source.include_exts = py,png,jpg,jpeg,kv,atlas,json,xlsx

version = 0.1
icon.filename = app_icon.png

requirements = python3,kivy,kivymd,openpyxl,et_xmlfile

orientation = portrait
fullscreen = 0

osx.python_version = 3
osx.kivy_version = 2.3.0

android.api = 33
android.minapi = 21
android.archs = arm64-v8a, armeabi-v7a

[buildozer]
log_level = 2
warn_on_root = 1
