# my_todo_MCPServer

[**my_todo**](https://github.com/nextxyz/my_todo) FastAPI TODO 앱의 REST API를 **MCP tool 로 감싼** MCP 서버.
Claude Code 가 자연어로 tool 을 호출하면, 이 서버가 내부적으로 `httpx` 로 FastAPI 를 호출한다.

```
사용자(자연어) → Claude Code → MCP(todo 서버) → httpx → FastAPI(todo_app) → SQLite
```

## 구성

- `server.py` — FastMCP 서버. `@mcp.tool()` 함수 6개가 LLM 이 쓸 도구가 된다.
- `requirements.txt` — `mcp`, `httpx`

## 제공하는 tool

| tool | 동작 | 감싸는 엔드포인트 |
|---|---|---|
| `add_todo(date, content)` | 추가 | `POST /todos` |
| `list_todos(date?, start?, end?, done?)` | 조회/필터 | `GET /todos` |
| `update_todo(todo_id, content?, date?)` | 내용/날짜 수정 | `PATCH /todos/{id}` |
| `complete_todo(todo_id)` | 완료 | `PATCH /todos/{id}/done` |
| `uncomplete_todo(todo_id)` | 완료취소 | `PATCH /todos/{id}/undone` |
| `delete_todo(todo_id)` | 삭제 | `DELETE /todos/{id}` |

## 셋업

```bash
git clone https://github.com/nextxyz/my_todo_MCPServer.git
cd my_todo_MCPServer
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

## 실행 순서

1. **FastAPI 앱을 먼저 띄운다** (MCP 서버가 호출할 대상 — [my_todo](https://github.com/nextxyz/my_todo)):
   ```bash
   git clone https://github.com/nextxyz/my_todo.git
   cd my_todo && ./run.sh   # http://localhost:8000
   ```
2. **Claude Code 에 MCP 서버 등록** (1회만, MCP 서버 폴더에서 실행):
   ```bash
   claude mcp add todo -- "$(pwd)/.venv/bin/python" "$(pwd)/server.py"
   ```
   - Claude Code 가 이 서버 프로세스를 stdio 로 띄워서 통신한다.
   - 등록 확인: `claude mcp list` → `todo ... ✔ Connected`
   - 해제: `claude mcp remove todo`
3. **Claude Code 를 새로 시작**하면 todo tool 들이 로드된다.

## 써보기 (Claude Code 에게 자연어로)

- "오늘 할 일 목록 보여줘"
- "내일 '코드리뷰 받기' 추가해줘"
- "3번 할 일 완료 처리해줘"
- "이번 주 미완료 할 일만 보여줘"

## 설정

- `TODO_API_BASE` 환경변수로 FastAPI 주소를 바꿀 수 있다 (기본 `http://localhost:8000`).

## 주의

- 이 MCP 는 실제 todo DB 를 그대로 변경한다. 테스트할 때는 별도 DB 를 쓰는 게 안전하다:
  ```bash
  # todo_app 쪽에서
  DATABASE_URL=sqlite:///./todo_test.db ./run.sh
  ```
