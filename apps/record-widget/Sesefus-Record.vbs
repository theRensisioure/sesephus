' Pin this / Start Menu "Sesefus Record" — not a raw console forever.
Option Explicit
Dim sh, fso, app, exe, ui
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
app = fso.GetParentFolderName(WScript.ScriptFullName)
exe = app & "\out\sesefus-record.exe"
If Not fso.FileExists(exe) Then
  MsgBox "Build first: run build.bat in " & app, 16, "Sesefus Record"
  WScript.Quit 1
End If
sh.CurrentDirectory = app & "\out"
' 1 = normal window so you see log; switch to 0 if you want quiet
sh.Run """" & exe & """", 1, False
' open browser app if Brave/Edge present
Dim brave, edge
brave = "C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
WScript.Sleep 600
If fso.FileExists(brave) Then
  sh.Run """" & brave & """ --app=http://127.0.0.1:8778/ --new-window", 1, False
ElseIf fso.FileExists(edge) Then
  sh.Run """" & edge & """ --app=http://127.0.0.1:8778/ --new-window", 1, False
Else
  sh.Run "http://127.0.0.1:8778/"
End If
