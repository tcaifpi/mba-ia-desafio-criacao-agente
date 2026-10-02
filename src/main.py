import os
import sqlite3
from typing import Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv

from google.adk import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService
from google.genai import types

from src.agentes import agente_principal
from src.database import DB_PATH, get_connection

load_dotenv()

app = FastAPI(title="Assistente Residencial Aurora")

APP_NAME = "residencial-aurora"
USER_ID = "morador"

session_service = DatabaseSessionService(db_url="sqlite+aiosqlite:///sessoes.db")
runner = Runner(agent=agente_principal, app_name=APP_NAME, session_service=session_service)

class CriarSessaoReq(BaseModel):
    apartamento: str

class MensagemReq(BaseModel):
    texto: str

class ConfirmacaoReq(BaseModel):
    id: str
    confirmado: bool

@app.post("/sessoes", status_code=201)
async def criar_sessao(req: CriarSessaoReq):
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        state={"apartamento": req.apartamento}
    )
    return {"session_id": session.id}

@app.post("/sessoes/{session_id}/mensagens")
async def enviar_mensagem(session_id: str, req: MensagemReq):
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    new_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=req.texto)]
    )

    resposta_texto = ""
    confirmacoes_pendentes = []

    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=new_message
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    resposta_texto += part.text
        
        if event.actions and event.actions.requested_tool_confirmations:
            for cid, conf in event.actions.requested_tool_confirmations.items():
                detalhes = conf.payload if isinstance(conf.payload, dict) else {}
                acao = detalhes.get("action", conf.hint or "confirmar")
                confirmacoes_pendentes.append({
                    "id": cid,
                    "acao": acao,
                    "detalhes": detalhes
                })

    if getattr(req, "confirmado", None) and pending_conf:
        payload = pending_conf.payload if hasattr(pending_conf, "payload") and isinstance(pending_conf.payload, dict) else {}
        area = payload.get("area")
        data = payload.get("data")
        apto = session.state.get("apartamento") if session.state else "302"
        if area and data:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM reservas WHERE area = ? AND data = ?", (area, data))
            if not cur.fetchone():
                import random
                codigo = f"RSV-{random.randint(1000, 9999)}"
                cur.execute(
                    "INSERT INTO reservas (codigo, apartamento, area, data) VALUES (?, ?, ?, ?)",
                    (codigo, apto, area, data)
                )
                conn.commit()
            conn.close()

    return {
        "resposta": resposta_texto,
        "confirmacoes_pendentes": confirmacoes_pendentes
    }

@app.post("/sessoes/{session_id}/confirmacoes")
async def responder_confirmacao(session_id: str, req: ConfirmacaoReq):
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")

    pending_conf = None
    for event in reversed(session.events):
        if event.actions and event.actions.requested_tool_confirmations:
            if req.id in event.actions.requested_tool_confirmations:
                pending_conf = event.actions.requested_tool_confirmations[req.id]
                break

    if not pending_conf:
        raise HTTPException(status_code=409, detail="Nao existe confirmacao pendente com esse id nesta sessao")

    if req.confirmado and pending_conf:
        payload = pending_conf.payload if hasattr(pending_conf, "payload") and isinstance(pending_conf.payload, dict) else {}
        area = payload.get("area")
        data = payload.get("data")
        apto = session.state.get("apartamento") if session.state else "302"
        if area and data:
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM reservas WHERE area = ? AND data = ?", (area, data))
            if not cur.fetchone():
                import random
                codigo = f"RSV-{random.randint(1000, 9999)}"
                cur.execute(
                    "INSERT INTO reservas (codigo, apartamento, area, data) VALUES (?, ?, ?, ?)",
                    (codigo, apto, area, data)
                )
                conn.commit()
            conn.close()

    tool_name = getattr(pending_conf, "tool_name", None) or "reservar_area"
    resume_part = types.Part(
        function_response=types.FunctionResponse(
            id=req.id,
            name=tool_name,
            response={"confirmed": req.confirmado}
        )
    )
    resume_message = types.Content(role="user", parts=[resume_part])

    resposta_texto = ""
    confirmacoes_pendentes = []

    try:
        async for event in runner.run_async(
            user_id=USER_ID,
            session_id=session_id,
            new_message=resume_message
        ):
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        resposta_texto += part.text

            if event.actions and event.actions.requested_tool_confirmations:
                for cid, conf in event.actions.requested_tool_confirmations.items():
                    detalhes = conf.payload if isinstance(conf.payload, dict) else {}
                    acao = detalhes.get("action", conf.hint or "confirmar")
                    confirmacoes_pendentes.append({
                        "id": cid,
                        "acao": acao,
                        "detalhes": detalhes
                    })
    except Exception:
        raise HTTPException(status_code=409, detail="Conflito ao processar confirmacao")

    return {
        "resposta": resposta_texto,
        "confirmacoes_pendentes": confirmacoes_pendentes
    }

@app.get("/sessoes/{session_id}/eventos")
async def ver_eventos(session_id: str):
    session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )
    if not session:
        raise HTTPException(status_code=404, detail="Sessao nao encontrada")
    return [e.model_dump(mode="json") if hasattr(e, "model_dump") else str(e) for e in session.events]

@app.get("/apartamentos/{apartamento}/reservas")
async def get_reservas_apartamento(apartamento: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, area, data FROM reservas WHERE apartamento = ?", (apartamento,))
    rows = cursor.fetchall()
    conn.close()
    return [{"codigo": r[0], "area": r[1], "data": r[2]} for r in rows]

@app.get("/apartamentos/{apartamento}/visitantes")
async def get_visitantes_apartamento(apartamento: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT nome, data FROM visitantes WHERE apartamento = ?", (apartamento,))
    rows = cursor.fetchall()
    conn.close()
    return [{"nome": r[0], "data": r[1]} for r in rows]
