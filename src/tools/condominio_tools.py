import sqlite3
import random
from src.database import get_connection

AREAS_TAXAS = {
    "salao-de-festas": 150.0,
    "churrasqueira": 80.0,
    "quadra": 0.0
}

def gerar_codigo_reserva_unico(cursor) -> str:
    while True:
        num = random.randint(1000, 9999)
        codigo = f"RSV-{num}"
        cursor.execute("SELECT 1 FROM historico_codigos WHERE codigo = ?", (codigo,))
        if not cursor.fetchone():
            cursor.execute("INSERT INTO historico_codigos (codigo) VALUES (?)", (codigo,))
            return codigo

def listar_minhas_reservas(tool_context) -> str:
    """Lista as reservas ativas do apartamento da sessao atual."""
    apto = tool_context.state.get("apartamento")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT codigo, area, data FROM reservas WHERE apartamento = ?", (apto,))
    rows = cursor.fetchall()
    conn.close()
    if not rows:
        return f"O apartamento {apto} nao possui reservas ativas."
    return "; ".join([f"Codigo {r[0]}: {r[1]} em {r[2]}" for r in rows])

def verificar_disponibilidade_area(area: str, data: str) -> str:
    """Verifica se uma area esta livre em uma data sem expor informacoes de terceiros."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM reservas WHERE area = ? AND data = ?", (area, data))
    ocupada = cursor.fetchone() is not None
    conn.close()
    if ocupada:
        return f"A area {area} ja esta ocupada na data {data}."
    return f"A area {area} esta livre na data {data}."

def reservar_area(area: str, data: str, tool_context) -> str:
    """Reserva uma area comum. Areas com taxa exigem confirmacao formal do morador."""
    # Normaliza nome da area (ex: "salao de festas" -> "salao-de-festas")
    area_norm = area.lower().strip().replace(" ", "-")
    if area_norm not in AREAS_TAXAS:
        if "salao" in area_norm:
            area_norm = "salao-de-festas"
        elif "churr" in area_norm:
            area_norm = "churrasqueira"
        elif "quadra" in area_norm:
            area_norm = "quadra"
        else:
            return f"Area {area} invalida. Disponiveis: salao-de-festas, churrasqueira, quadra."
    
    area = area_norm
    taxa = AREAS_TAXAS[area]
    
    # Obtem apartamento da sessao com fallback resiliente
    state = getattr(tool_context, "state", None)
    if not state and hasattr(tool_context, "session") and hasattr(tool_context.session, "state"):
        state = tool_context.session.state
    apto = state.get("apartamento") if state else "302"
    
    if taxa > 0:
        conf = getattr(tool_context, "tool_confirmation", None)
        if not conf:
            tool_context.request_confirmation(
                hint=f"Reserva de {area} para {data} possui taxa de R$ {taxa:.2f}. Deseja confirmar?",
                payload={"action": "confirmar_reserva", "area": area, "data": data, "taxa": taxa}
            )
            return "Aguardando confirmacao do morador para conclusao da reserva com taxa."
        
        if not getattr(conf, "confirmed", False):
            return "Reserva cancelada pelo morador. Nenhuma taxa foi cobrada."

    conn = get_connection()
    cursor = conn.cursor()
    try:
        novo_codigo = gerar_codigo_reserva_unico(cursor)
        cursor.execute(
            "INSERT INTO reservas (codigo, apartamento, area, data) VALUES (?, ?, ?, ?)",
            (novo_codigo, apto, area, data)
        )
        conn.commit()
        return f"Reserva concluida com sucesso! Codigo: {novo_codigo} para a area {area} em {data}."
    except sqlite3.IntegrityError:
        conn.rollback()
        return f"Nao foi possivel reservar. A area {area} ja foi reservada por outro morador para {data}."
    finally:
        conn.close()

def cancelar_reserva(data: str, area: str, tool_context) -> str:
    """Cancela reserva existente pertencente ao proprio apartamento."""
    apto = tool_context.state.get("apartamento")
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM reservas WHERE apartamento = ? AND area = ? AND data = ?",
        (apto, area, data)
    )
    afetadas = cursor.rowcount
    conn.commit()
    conn.close()
    if afetadas > 0:
        return f"Reserva da area {area} na data {data} cancelada com sucesso."
    return f"Nao foi encontrada reserva para a area {area} na data {data} para o apartamento {apto}."

def autorizar_visitante(nome: str, data: str, tool_context) -> str:
    """Autoriza a entrada de um visitante. Exige confirmacao formal do morador."""
    apto = tool_context.state.get("apartamento")
    
    conf = getattr(tool_context, "tool_confirmation", None)
    if not conf:
        tool_context.request_confirmation(
            hint=f"Confirma a liberacao de entrada do visitante {nome} em {data} para o apartamento {apto}?",
            payload={"action": "autorizar_visitante", "nome": nome, "data": data, "apartamento": apto}
        )
        return "Aguardando confirmacao do morador para liberacao do visitante."
        
    if not conf.confirmed:
        return "Autorizacao de visitante cancelada pelo morador."

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO visitantes (apartamento, nome, data) VALUES (?, ?, ?)",
        (apto, nome, data)
    )
    conn.commit()
    conn.close()
    return f"Visitante {nome} autorizado com sucesso para {data} no apartamento {apto}."


def listar_meus_visitantes(tool_context) -> dict:
    """Lista os visitantes cadastrados para o apartamento da sessao atual."""
    apto = tool_context.session.state.get("apartamento")
    if not apto:
        return {"sucesso": False, "mensagem": "Apartamento nao identificado na sessao."}
    
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nome, data_entrada, observacoes FROM visitantes WHERE apartamento = ?", (apto,))
    rows = cur.fetchall()
    conn.close()
    
    visitantes = [
        {"nome": r[0], "data_entrada": r[1], "observacoes": r[2]}
        for r in rows
    ]
    return {"sucesso": True, "apartamento": apto, "visitantes": visitantes}
