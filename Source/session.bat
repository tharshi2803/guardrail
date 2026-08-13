for %%i in (1 2 3) do (
curl -s -o NUL -w "request %%i -> HTTP %%{http_code}\n" ^
http://localhost:8000/query ^
-H "Content-Type: application/json" ^
-d "{\"question\":\"What allergy categories are present?\",\"session_id\":\"rate-demo\"}"
)