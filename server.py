"""
TODO MCP 서버

기존 FastAPI TODO 앱(http://localhost:8000)의 REST API를
MCP tool 로 감싼다. Claude(또는 다른 MCP 클라이언트)가 자연어로
이 tool 들을 호출하면, 내부적으로 httpx 로 FastAPI 를 호출한다.

핵심 개념:
- @mcp.tool() 데코레이터를 붙인 함수 하나하나가 LLM 이 쓸 수 있는 "도구"가 된다.
- 함수의 타입힌트 -> tool 의 inputSchema(JSON Schema) 로 자동 변환된다.
- 함수의 docstring -> tool 의 description 이 된다.
  LLM 은 이 description 을 보고 "언제 이 도구를 쓸지" 판단하므로, 설명을 잘 쓰는 게 제일 중요하다.
"""

import os
from typing import Optional

import httpx
from mcp.server.fastmcp import FastMCP

# FastAPI 앱의 베이스 URL (환경변수로 덮어쓸 수 있음)
API_BASE = os.getenv("TODO_API_BASE", "http://localhost:8000")

# MCP 서버 인스턴스. 이름은 클라이언트에서 이 서버를 식별하는 데 쓰인다.
mcp = FastMCP("todo")


async def _request(method: str, path: str, **kwargs) -> httpx.Response:
    """FastAPI 로 HTTP 요청을 보내는 얇은 헬퍼.

    에러가 나면 LLM 이 이해할 수 있는 메시지로 바꿔서 예외를 던진다.
    (MCP 는 예외 메시지를 tool 실행 결과로 LLM 에게 전달한다.)
    """
    url = f"{API_BASE}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.request(method, url, **kwargs)
        except httpx.ConnectError as e:
            raise RuntimeError(
                f"TODO API({API_BASE})에 연결할 수 없습니다. "
                f"FastAPI 서버가 실행 중인지 확인하세요. ({e})"
            )
    if resp.status_code == 404:
        raise RuntimeError("해당 ID의 할 일을 찾을 수 없습니다.")
    resp.raise_for_status()
    return resp


@mcp.tool()
async def add_todo(date: str, content: str) -> dict:
    """할 일을 새로 추가한다.

    Args:
        date: 할 일 날짜, YYYY-MM-DD 형식 (예: "2026-06-16")
        content: 할 일 내용 (예: "MCP 서버 공부하기")

    Returns:
        생성된 할 일 정보 (id 포함)
    """
    resp = await _request("POST", "/todos", json={"date": date, "content": content})
    return resp.json()


@mcp.tool()
async def list_todos(
    date: Optional[str] = None,
    start: Optional[str] = None,
    end: Optional[str] = None,
    done: Optional[bool] = None,
) -> list[dict]:
    """할 일 목록을 조회한다. 모든 인자는 선택이며, 조합해서 필터링할 수 있다.

    Args:
        date: 특정 날짜만 조회 (YYYY-MM-DD)
        start: 기간 조회 시작일(포함, YYYY-MM-DD)
        end: 기간 조회 종료일(포함, YYYY-MM-DD)
        done: 완료 여부 필터. True=완료된 것만, False=미완료만, 생략=전체

    Returns:
        조건에 맞는 할 일 목록. 인자를 모두 생략하면 전체를 반환한다.
    """
    params = {}
    if date is not None:
        params["date"] = date
    if start is not None:
        params["start"] = start
    if end is not None:
        params["end"] = end
    if done is not None:
        params["done"] = done
    resp = await _request("GET", "/todos", params=params)
    return resp.json()


@mcp.tool()
async def update_todo(
    todo_id: int,
    content: Optional[str] = None,
    date: Optional[str] = None,
) -> dict:
    """기존 할 일의 내용 또는 날짜를 수정한다. content, date 중 보낸 것만 변경된다.

    Args:
        todo_id: 수정할 할 일의 id
        content: 새 내용 (생략 시 변경 안 함)
        date: 새 날짜 YYYY-MM-DD (생략 시 변경 안 함)

    Returns:
        수정된 할 일 정보
    """
    payload = {}
    if content is not None:
        payload["content"] = content
    if date is not None:
        payload["date"] = date
    resp = await _request("PATCH", f"/todos/{todo_id}", json=payload)
    return resp.json()


@mcp.tool()
async def complete_todo(todo_id: int) -> dict:
    """할 일을 '완료' 상태로 표시한다.

    Args:
        todo_id: 완료 처리할 할 일의 id

    Returns:
        갱신된 할 일 정보 (done=true)
    """
    resp = await _request("PATCH", f"/todos/{todo_id}/done")
    return resp.json()


@mcp.tool()
async def uncomplete_todo(todo_id: int) -> dict:
    """완료했던 할 일을 다시 '미완료' 상태로 되돌린다.

    Args:
        todo_id: 미완료로 되돌릴 할 일의 id

    Returns:
        갱신된 할 일 정보 (done=false)
    """
    resp = await _request("PATCH", f"/todos/{todo_id}/undone")
    return resp.json()


@mcp.tool()
async def delete_todo(todo_id: int) -> str:
    """할 일을 삭제한다. (완료/미완료 상관없이 제거)

    Args:
        todo_id: 삭제할 할 일의 id

    Returns:
        삭제 완료 메시지
    """
    await _request("DELETE", f"/todos/{todo_id}")
    return f"id={todo_id} 할 일을 삭제했습니다."


if __name__ == "__main__":
    # stdio transport 로 MCP 서버를 실행한다.
    # Claude Code 같은 클라이언트가 이 프로세스를 띄우고 stdin/stdout 으로 통신한다.
    mcp.run()
