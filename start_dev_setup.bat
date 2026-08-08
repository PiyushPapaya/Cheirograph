@echo off
REM Starts the Cheirograph dev setup: dashboard in incognito Chrome, Arduino IDE, VS Code on this folder.

start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --incognito "C:\Users\anil1\Downloads\Cheirograph\tools\handrig_dashboard.html"

start "" "C:\Users\anil1\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Arduino IDE.lnk"

start "" "C:\Users\anil1\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Visual Studio Code.lnk" "C:\Users\anil1\Downloads\Cheirograph"
