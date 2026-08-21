' Skills window — pin this. No console.
Option Explicit
Dim sh, fso, app, host, logf, pyw, py, data
Set sh = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
app = fso.GetParentFolderName(WScript.ScriptFullName)
host = app & "\host.py"
data = sh.ExpandEnvironmentStrings("%LOCALAPPDATA%") & "\Sesefus"
If Not fso.FolderExists(data) Then fso.CreateFolder data
logf = data & "\skills-window-launch.log"
sh.CurrentDirectory = app

Dim log
Set log = fso.OpenTextFile(logf, 8, True)
log.WriteLine "==== " & Now & " (Skills.vbs) ===="
log.WriteLine "APP=" & app

pyw = ""
py = ""
Dim la
la = sh.ExpandEnvironmentStrings("%LocalAppData%")
If fso.FileExists(la & "\Programs\Python\Python312\pythonw.exe") Then
  pyw = la & "\Programs\Python\Python312\pythonw.exe"
ElseIf fso.FileExists(la & "\Programs\Python\Python311\pythonw.exe") Then
  pyw = la & "\Programs\Python\Python311\pythonw.exe"
ElseIf fso.FileExists(la & "\Programs\Python\Python314\pythonw.exe") Then
  pyw = la & "\Programs\Python\Python314\pythonw.exe"
End If
If fso.FileExists(la & "\Programs\Python\Python312\python.exe") Then
  py = la & "\Programs\Python\Python312\python.exe"
ElseIf fso.FileExists(la & "\Programs\Python\Python311\python.exe") Then
  py = la & "\Programs\Python\Python311\python.exe"
ElseIf fso.FileExists(la & "\Programs\Python\Python314\python.exe") Then
  py = la & "\Programs\Python\Python314\python.exe"
End If

Dim cmd
If pyw <> "" Then
  log.WriteLine "using PYW=" & pyw
  cmd = """" & pyw & """ """ & host & """"
ElseIf py <> "" Then
  log.WriteLine "using PY=" & py
  cmd = """" & py & """ """ & host & """"
Else
  log.WriteLine "No Python"
  log.Close
  MsgBox "Skills window: no Python found (need 3.11+).", 16, "Skills"
  WScript.Quit 1
End If
log.Close
sh.Run cmd, 0, False
WScript.Quit 0
