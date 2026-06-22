@echo off
cd /d "%~dp0"

python -m nuitka ^
--standalone ^
--onefile ^
--windows-console-mode=disable ^
--remove-output ^
--enable-plugin=tk-inter ^
--windows-icon-from-ico="icon.ico" ^
--assume-yes-for-downloads ^
--python-flag=-O ^
game_save_manager.py