Set ws = CreateObject("WScript.Shell")
Set http = CreateObject("MSXML2.ServerXMLHTTP.6.0")

' Start backend with scalping env vars
cmd = "cmd /c set STRATEGY=scalping && set MIN_CONFIDENCE=60 && set MAX_RISK_PER_TRADE=0.01 && cd /d A:\trading agent\backend && uvicorn app.main:app --host 0.0.0.0 --port 8000"
ws.Run cmd, 0, False

WScript.Sleep 15000

On Error Resume Next
http.open "POST", "http://localhost:8000/api/trade/start", False
http.setRequestHeader "Content-Type", "application/json"
http.send ""

http.open "POST", "http://localhost:8000/api/trade/reset-drawdown", False
http.setRequestHeader "Content-Type", "application/json"
http.send ""
On Error Goto 0
