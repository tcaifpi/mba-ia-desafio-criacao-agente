import sqlite3
import json
import os

DB_PATH = "condominio.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, timeout=20.0)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reservas (
            codigo TEXT PRIMARY KEY,
            apartamento TEXT NOT NULL,
            area TEXT NOT NULL,
            data TEXT NOT NULL,
            UNIQUE(area, data)
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS historico_codigos (
            codigo TEXT PRIMARY KEY
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS visitantes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apartamento TEXT NOT NULL,
            nome TEXT NOT NULL,
            data TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()

def restaurar_dados():
    init_db()
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM reservas")
    cursor.execute("DELETE FROM visitantes")
    cursor.execute("DELETE FROM historico_codigos")
    
    base_dir = os.path.join(os.path.dirname(__file__), "..", "dados")
    
    with open(os.path.join(base_dir, "reservas.json"), "r", encoding="utf-8") as f:
        reservas = json.load(f)
        for r in reservas:
            cursor.execute(
                "INSERT INTO reservas (codigo, apartamento, area, data) VALUES (?, ?, ?, ?)",
                (r["codigo"], r["apartamento"], r["area"], r["data"])
            )
            cursor.execute("INSERT INTO historico_codigos (codigo) VALUES (?)", (r["codigo"],))
            
    with open(os.path.join(base_dir, "visitantes.json"), "r", encoding="utf-8") as f:
        visitantes = json.load(f)
        for v in visitantes:
            cursor.execute(
                "INSERT INTO visitantes (apartamento, nome, data) VALUES (?, ?, ?)",
                (v["apartamento"], v["nome"], v["data"])
            )
            
    conn.commit()
    conn.close()

if __name__ == "__main__":
    restaurar_dados()
    print("Dados restaurados com sucesso em condominio.db")
