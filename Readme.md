# 실행방법

## B/E 서버 구동
```
py -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload or uvicorn app.main:app --reload --port 8001
```

## 테스트 코드 실행
### DB 초기화 (최초 1회)
```
py -3.12 scripts/init_db.py
```

### 전체 테스트 실행
```
py -3.12 -m pytest tests/ -v
```

### 특정 파일만 실행
```
py -3.12 -m pytest tests/test_scenarios.py -v
```