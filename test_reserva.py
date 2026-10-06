import pytest
import httpx
import sqlite3

BASE_URL = "http://localhost:8000"

@pytest.fixture(autouse=True)
def clean_db():
    conn = sqlite3.connect("condominio.db")
    cur = conn.cursor()
    cur.execute("DELETE FROM reservas WHERE data IN ('2026-11-20', '2026-12-10', '2026-12-15')")
    conn.commit()
    conn.close()
    yield

@pytest.mark.anyio
async def test_reserva_com_confirmacao():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        # 1. Cria sessao
        r = await client.post("/sessoes", json={"apartamento": "302"})
        assert r.status_code in (200, 201)
        sid = r.json()["session_id"]

        # 2. Solicita salao de festas (possui taxa)
        r = await client.post(f"/sessoes/{sid}/mensagens", json={"texto": "Quero reservar o salao de festas para 2026-11-20."})
        assert r.status_code in (200, 201)
        data = r.json()
        assert len(data.get("confirmacoes_pendentes", [])) > 0
        cid = data["confirmacoes_pendentes"][0]["id"]

        # 3. Confirma reserva
        r = await client.post(f"/sessoes/{sid}/confirmacoes", json={"id": cid, "confirmado": True})
        assert r.status_code in (200, 201)

        # 4. Checa banco
        r = await client.get("/apartamentos/302/reservas")
        assert r.status_code in (200, 201)
        reservas = r.json()
        assert any(res["area"] == "salao-de-festas" and res["data"] == "2026-11-20" for res in reservas)

@pytest.mark.anyio
async def test_recusa_confirmacao():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        # 1. Cria sessao
        r = await client.post("/sessoes", json={"apartamento": "302"})
        assert r.status_code in (200, 201)
        sid = r.json()["session_id"]

        # 2. Solicita churrasqueira (possui taxa)
        r = await client.post(f"/sessoes/{sid}/mensagens", json={"texto": "Quero reservar a churrasqueira para 2026-12-10."})
        assert r.status_code in (200, 201)
        data = r.json()
        assert len(data.get("confirmacoes_pendentes", [])) > 0
        cid = data["confirmacoes_pendentes"][0]["id"]

        # 3. Recusa reserva
        r = await client.post(f"/sessoes/{sid}/confirmacoes", json={"id": cid, "confirmado": False})
        assert r.status_code in (200, 201)

        # 4. Checa banco (nao deve constar)
        r = await client.get("/apartamentos/302/reservas")
        assert r.status_code in (200, 201)
        reservas = r.json()
        assert not any(res["area"] == "churrasqueira" and res["data"] == "2026-12-10" for res in reservas)

@pytest.mark.anyio
async def test_reserva_sem_taxa():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=60.0) as client:
        # 1. Cria sessao
        r = await client.post("/sessoes", json={"apartamento": "302"})
        assert r.status_code in (200, 201)
        sid = r.json()["session_id"]

        # 2. Solicita quadra (sem taxa)
        r = await client.post(f"/sessoes/{sid}/mensagens", json={"texto": "Quero reservar a quadra para 2026-12-15."})
        assert r.status_code in (200, 201)
        data = r.json()
        assert len(data.get("confirmacoes_pendentes", [])) == 0

        # 3. Checa banco
        r = await client.get("/apartamentos/302/reservas")
        assert r.status_code in (200, 201)
        reservas = r.json()
        assert any(res["area"] == "quadra" and res["data"] == "2026-12-15" for res in reservas)
