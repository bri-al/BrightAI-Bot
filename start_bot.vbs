Set ws = CreateObject("WScript.Shell")
Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")

' Start the backend server (hidden, async)
ws.Run "cmd /c cd /d A:\trading agent\backend && uvicorn app.main:app --host 0.0.0.0 --port 8000", 0, False

' Wait for server to start
WScript.Sleep 15000

' Reset drawdown so bot can trade immediately
On Error Resume Next
http.open "POST", "http://localhost:8000/api/trade/reset-drawdown", False
http.setRequestHeader "Content-Type", "application/json"
http.send ""
On Error Goto 0
