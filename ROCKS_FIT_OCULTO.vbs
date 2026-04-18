Set WshShell = CreateObject("WScript.Shell")
' Executa o arquivo abrir_catraca.bat em modo oculto (0)
WshShell.Run chr(34) & "abrir_catraca.bat" & chr(34), 0
Set WshShell = Nothing
