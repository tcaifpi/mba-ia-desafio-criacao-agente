import os

MAPA_CAPITULOS = {
    "piscina": "Capítulo IV: Piscina",
    "silencio": "Capítulo III: Silêncio e boa convivência",
    "academia": "Capítulo V: Academia, brinquedoteca e playground",
    "brinquedoteca": "Capítulo V: Academia, brinquedoteca e playground",
    "playground": "Capítulo V: Academia, brinquedoteca e playground",
    "salao": "Capítulo VI: Salão de festas, churrasqueira e quadra",
    "churrasqueira": "Capítulo VI: Salão de festas, churrasqueira e quadra",
    "quadra": "Capítulo VI: Salão de festas, churrasqueira e quadra",
    "animais": "Capítulo VIII: Animais de estimação",
    "pet": "Capítulo VIII: Animais de estimação",
    "cachorro": "Capítulo VIII: Animais de estimação",
    "mudanca": "Capítulo IX: Mudanças",
    "obras": "Capítulo X: Obras e reformas",
    "reforma": "Capítulo X: Obras e reformas",
    "garagem": "Capítulo XI: Garagem e veículos",
    "veiculo": "Capítulo XI: Garagem e veículos",
    "vaga": "Capítulo XI: Garagem e veículos",
    "lixo": "Capítulo XII: Coleta de lixo e reciclagem"
}

def consultar_regulamento(tema: str) -> str:
    """Consulta regras no regulamento interno filtrando pelo tema informado."""
    tema_clean = tema.lower()
    cap_alvo = None
    for k, v in MAPA_CAPITULOS.items():
        if k in tema_clean:
            cap_alvo = v
            break
            
    base_path = os.path.join(os.path.dirname(__file__), "..", "..", "dados", "regulamento.md")
    with open(base_path, "r", encoding="utf-8") as f:
        texto = f.read()

    if not cap_alvo:
        return "Tema nao localizado especificamente. Temas disponiveis: piscina, silencio, academia, mudanca, garagem, lixo."

    partes = texto.split("## ")
    for p in partes:
        if p.startswith(cap_alvo) or cap_alvo in p:
            return f"Regras extraidas de {cap_alvo}:\n" + p.strip()

    return "Capitulo correspondente nao encontrado no regulamento."
