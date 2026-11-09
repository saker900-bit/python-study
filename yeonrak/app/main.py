"""연락각 – 이쯤 되면 연락해야 할 때를 알려주는 앱 (FastAPI 서버)."""
from __future__ import annotations

import asyncio
import os
import secrets
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from . import ai, db

TZ = ZoneInfo(os.environ.get("YEONRAK_TZ", "Asia/Seoul"))
CHECK_INTERVAL_SEC = int(os.environ.get("YEONRAK_CHECK_SEC", "60"))
NUDGE_COOLDOWN = timedelta(minutes=10)
STATIC = Path(__file__).parent / "static"

# 관계별 기본 "연락 텀" (시간)
DEFAULT_THRESHOLD = {"dating": 6, "spouse": 4, "parent": 72, "child": 72, "friend": 168}
RELATION_KO = {"dating": "연인", "spouse": "배우자", "parent": "부모님", "child": "자녀", "friend": "친구"}


def now() -> datetime:
    return datetime.now(TZ)


def iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def parse(s: str) -> datetime:
    return datetime.fromisoformat(s)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    task = asyncio.create_task(_reminder_loop()) if CHECK_INTERVAL_SEC > 0 else None
    yield
    if task:
        task.cancel()


app = FastAPI(title="연락각", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/")
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/sw.js")
def service_worker():
    # 서비스 워커는 루트 경로에서 서빙해야 전체 페이지를 제어할 수 있다.
    return FileResponse(STATIC / "sw.js", media_type="application/javascript")


# ---------- 인증 ----------

def current_user(x_token: str = Header(...)):
    with db.connect() as conn:
        row = conn.execute("SELECT * FROM users WHERE token = ?", (x_token,)).fetchone()
    if not row:
        raise HTTPException(401, "로그인이 필요해요")
    return dict(row)


# ---------- 요청 모델 ----------

class SignupIn(BaseModel):
    name: str = Field(min_length=1, max_length=30)


class LinkIn(BaseModel):
    invite_code: str
    relation: str = Field(pattern="^(dating|spouse|parent|child|friend)$")
    i_call_them: str = Field(min_length=1, max_length=20)   # 예: 엄마
    they_call_me: str = Field(min_length=1, max_length=20)  # 예: 아들
    threshold_hours: float | None = Field(default=None, gt=0, le=24 * 60)


class LinkPatch(BaseModel):
    threshold_hours: float = Field(gt=0, le=24 * 60)


class StatusIn(BaseModel):
    status: str | None = Field(default=None, max_length=40)


# ---------- 헬퍼 ----------

def _notify(conn, user_id: int, kind: str, title: str, body: str, link_id: int | None = None):
    conn.execute(
        "INSERT INTO notifications (user_id, kind, title, body, link_id, created_at) VALUES (?,?,?,?,?,?)",
        (user_id, kind, title, body, link_id, iso(now())),
    )


def _get_link(conn, link_id: int, user_id: int) -> dict:
    row = conn.execute(
        "SELECT * FROM links WHERE id = ? AND (user_a = ? OR user_b = ?)", (link_id, user_id, user_id)
    ).fetchone()
    if not row:
        raise HTTPException(404, "연결을 찾을 수 없어요")
    return dict(row)


def _view(link: dict, me: int) -> dict:
    """내 입장에서 본 연결 정보: 상대 id, 상대를 부르는 이름, 상대가 나를 부르는 이름."""
    if link["user_a"] == me:
        return {"other": link["user_b"], "their_name": link["a_calls_b"], "my_name": link["b_calls_a"]}
    return {"other": link["user_a"], "their_name": link["b_calls_a"], "my_name": link["a_calls_b"]}


def _hours_since(link: dict, at: datetime | None = None) -> float:
    return ((at or now()) - parse(link["last_contact_at"])).total_seconds() / 3600


def _link_out(conn, link: dict, me: int) -> dict:
    v = _view(link, me)
    other = conn.execute("SELECT name, status, status_at FROM users WHERE id = ?", (v["other"],)).fetchone()
    hrs = _hours_since(link)
    return {
        "id": link["id"],
        "their_name": v["their_name"],
        "their_account_name": other["name"],
        "their_status": other["status"],
        "relation": link["relation"],
        "relation_ko": RELATION_KO[link["relation"]],
        "threshold_hours": link["threshold_hours"],
        "last_contact_at": link["last_contact_at"],
        "hours_since": round(hrs, 2),
        "progress": round(min(hrs / link["threshold_hours"], 1.0), 3),
        "overdue": hrs >= link["threshold_hours"],
    }


def _usual_hours(conn, link_id: int, user_id: int) -> list[int]:
    rows = conn.execute(
        "SELECT at FROM contacts WHERE link_id = ? AND by_user = ? ORDER BY id DESC LIMIT 100",
        (link_id, user_id),
    ).fetchall()
    counts = Counter(parse(r["at"]).astimezone(TZ).hour for r in rows)
    return [h for h, _ in counts.most_common(3)]


# ---------- API ----------

@app.post("/api/users")
def signup(body: SignupIn):
    token = secrets.token_urlsafe(24)
    code = secrets.token_hex(3).upper()
    with db.connect() as conn:
        cur = conn.execute(
            "INSERT INTO users (name, token, invite_code) VALUES (?,?,?)", (body.name, token, code)
        )
        uid = cur.lastrowid
    return {"id": uid, "name": body.name, "token": token, "invite_code": code}


@app.get("/api/me")
def me(user=Depends(current_user)):
    return {k: user[k] for k in ("id", "name", "invite_code", "status")}


@app.post("/api/me/status")
def set_status(body: StatusIn, user=Depends(current_user)):
    status = (body.status or "").strip() or None
    with db.connect() as conn:
        conn.execute("UPDATE users SET status = ?, status_at = ? WHERE id = ?", (status, iso(now()), user["id"]))
    return {"status": status}


@app.post("/api/links")
def create_link(body: LinkIn, user=Depends(current_user)):
    with db.connect() as conn:
        other = conn.execute(
            "SELECT * FROM users WHERE invite_code = ?", (body.invite_code.strip().upper(),)
        ).fetchone()
        if not other:
            raise HTTPException(404, "초대 코드가 맞지 않아요")
        if other["id"] == user["id"]:
            raise HTTPException(400, "나 자신과는 연결할 수 없어요")
        dup = conn.execute(
            "SELECT 1 FROM links WHERE (user_a=? AND user_b=?) OR (user_a=? AND user_b=?)",
            (user["id"], other["id"], other["id"], user["id"]),
        ).fetchone()
        if dup:
            raise HTTPException(409, "이미 연결된 상대예요")
        t = iso(now())
        threshold = body.threshold_hours or DEFAULT_THRESHOLD[body.relation]
        cur = conn.execute(
            """INSERT INTO links (user_a, user_b, a_calls_b, b_calls_a, relation, threshold_hours,
                                  created_at, last_contact_at) VALUES (?,?,?,?,?,?,?,?)""",
            (user["id"], other["id"], body.i_call_them, body.they_call_me, body.relation, threshold, t, t),
        )
        _notify(conn, other["id"], "linked", "연결됐어요 🔗",
                f"{body.they_call_me}(으)로 {user['name']}님과 연결됐어요.", cur.lastrowid)
        link = _get_link(conn, cur.lastrowid, user["id"])
        return _link_out(conn, link, user["id"])


@app.get("/api/links")
def list_links(user=Depends(current_user)):
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM links WHERE user_a = ? OR user_b = ? ORDER BY id", (user["id"], user["id"])
        ).fetchall()
        out = [_link_out(conn, dict(r), user["id"]) for r in rows]
    return sorted(out, key=lambda l: -l["progress"])


@app.patch("/api/links/{link_id}")
def update_link(link_id: int, body: LinkPatch, user=Depends(current_user)):
    with db.connect() as conn:
        _get_link(conn, link_id, user["id"])
        conn.execute("UPDATE links SET threshold_hours = ? WHERE id = ?", (body.threshold_hours, link_id))
        return _link_out(conn, _get_link(conn, link_id, user["id"]), user["id"])


@app.post("/api/links/{link_id}/contact")
def log_contact(link_id: int, user=Depends(current_user)):
    """'연락했어요' 버튼. 연락 타이머를 초기화하고 상대에게 알린다."""
    with db.connect() as conn:
        link = _get_link(conn, link_id, user["id"])
        v = _view(link, user["id"])
        t = iso(now())
        conn.execute("INSERT INTO contacts (link_id, by_user, at) VALUES (?,?,?)", (link_id, user["id"], t))
        conn.execute("UPDATE links SET last_contact_at = ?, last_reminded_at = NULL WHERE id = ?", (t, link_id))
        _notify(conn, v["other"], "contact", f"{v['my_name']}한테서 연락 왔어요 💌",
                "연락 타이머가 초기화됐어요.", link_id)
        return _link_out(conn, _get_link(conn, link_id, user["id"]), user["id"])


@app.post("/api/links/{link_id}/nudge")
def nudge(link_id: int, user=Depends(current_user)):
    """'야 연락 안 하냐?' 버튼. 상대에게 푸시를 보낸다 (10분에 한 번)."""
    with db.connect() as conn:
        link = _get_link(conn, link_id, user["id"])
        v = _view(link, user["id"])
        last = conn.execute(
            "SELECT at FROM nudges WHERE link_id = ? AND from_user = ? ORDER BY id DESC LIMIT 1",
            (link_id, user["id"]),
        ).fetchone()
        if last and now() - parse(last["at"]) < NUDGE_COOLDOWN:
            wait = NUDGE_COOLDOWN - (now() - parse(last["at"]))
            raise HTTPException(429, f"재촉은 10분에 한 번만! {int(wait.total_seconds() // 60) + 1}분 뒤에 다시 눌러요")
        conn.execute("INSERT INTO nudges (link_id, from_user, at) VALUES (?,?,?)", (link_id, user["id"], iso(now())))
        _notify(conn, v["other"], "nudge", f"{v['my_name']}: 야 연락 안 하냐? 📢",
                f"{v['my_name']}이(가) 연락을 기다리고 있어요.", link_id)
    return {"ok": True}


@app.get("/api/links/{link_id}/reassure")
def reassure(link_id: int, user=Depends(current_user)):
    """상대가 연락이 없을 때 안심 멘트."""
    with db.connect() as conn:
        link = _get_link(conn, link_id, user["id"])
        v = _view(link, user["id"])
        other = conn.execute("SELECT status, status_at FROM users WHERE id = ?", (v["other"],)).fetchone()
        status = other["status"]
        # 12시간 넘은 상태는 오래된 정보라 무시
        if status and other["status_at"] and now() - parse(other["status_at"]) > timedelta(hours=12):
            status = None
        sit = ai.Situation(
            their_name=v["their_name"],
            relation=RELATION_KO[link["relation"]],
            now=now(),
            hours_since=_hours_since(link),
            their_status=status,
            usual_hours=_usual_hours(conn, link_id, v["other"]),
        )
    return ai.reassure(sit)


@app.get("/api/notifications")
def poll_notifications(user=Depends(current_user)):
    """아직 안 받은 알림을 돌려주고 받은 것으로 표시한다. 앱이 주기적으로 호출."""
    with db.connect() as conn:
        rows = conn.execute(
            "SELECT * FROM notifications WHERE user_id = ? AND delivered = 0 ORDER BY id", (user["id"],)
        ).fetchall()
        if rows:
            conn.execute(
                f"UPDATE notifications SET delivered = 1 WHERE id IN ({','.join('?' * len(rows))})",
                [r["id"] for r in rows],
            )
    return [dict(r) for r in rows]


# ---------- 리마인더 ----------

def check_reminders(at: datetime | None = None) -> int:
    """연락 텀을 넘긴 연결마다 양쪽에 '이쯤 되면 연락해야죠' 알림을 한 번씩 보낸다."""
    at = at or now()
    sent = 0
    with db.connect() as conn:
        rows = conn.execute("SELECT * FROM links WHERE last_reminded_at IS NULL").fetchall()
        for r in rows:
            link = dict(r)
            if _hours_since(link, at) < link["threshold_hours"]:
                continue
            hrs = _hours_since(link, at)
            ago = f"{int(hrs * 60)}분" if hrs < 1 else f"{int(hrs)}시간" if hrs < 48 else f"{int(hrs // 24)}일"
            for uid in (link["user_a"], link["user_b"]):
                v = _view(link, uid)
                _notify(conn, uid, "reminder", f"{v['their_name']}한테 연락할 각 ⏰",
                        f"마지막 연락 후 {ago} 지났어요. 이쯤 되면 연락 한번 해줘야죠!", link["id"])
                sent += 1
            conn.execute("UPDATE links SET last_reminded_at = ? WHERE id = ?", (iso(at), link["id"]))
    return sent


async def _reminder_loop():
    while True:
        try:
            await asyncio.to_thread(check_reminders)
        except Exception:  # 루프가 죽지 않게
            import logging
            logging.exception("reminder check failed")
        await asyncio.sleep(CHECK_INTERVAL_SEC)
