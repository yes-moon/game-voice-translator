' 게임 음성 번역기 — 더블클릭 실행기 (콘솔 창 없이 GUI만 실행)
Set fso = CreateObject("Scripting.FileSystemObject")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
Set sh = CreateObject("WScript.Shell")
sh.CurrentDirectory = folder
' 0 = 창 숨김(콘솔 없음), False = 종료를 기다리지 않음
sh.Run """" & folder & "\.venv\Scripts\pythonw.exe"" """ & folder & "\gui.py""", 0, False
