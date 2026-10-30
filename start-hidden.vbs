' Launches start-bot.bat with no visible window (used by Task Scheduler).
Set fso = CreateObject("Scripting.FileSystemObject")
Set shell = CreateObject("WScript.Shell")
folder = fso.GetParentFolderName(WScript.ScriptFullName)
shell.CurrentDirectory = folder
shell.Run folder & "\start-bot.bat", 0, False
