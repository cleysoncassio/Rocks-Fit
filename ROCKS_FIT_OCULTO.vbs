Set WshShell = CreateObject("WScript.Shell")
Set fso = CreateObject("Scripting.FileSystemObject")
' Obtém a pasta onde este script VBS está localizado
strPath = fso.GetParentFolderName(WScript.ScriptFullName)
' Define o diretório de trabalho como a pasta do script
WshShell.CurrentDirectory = strPath
' Executa o arquivo abrir_catraca.bat em modo oculto (0)
WshShell.Run chr(34) & "abrir_catraca.bat" & chr(34), 0
Set WshShell = Nothing
Set fso = Nothing
