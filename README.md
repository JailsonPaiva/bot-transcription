para iniciar o ngrok 
```shell
    ngrok http 8000
```

para iniciar o projeto
```python
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```