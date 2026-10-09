"""# Assistente Virtual - Residencial Aurora

API do assistente virtual do Residencial Aurora, desenvolvida em Python 3.12 com Google ADK 2.2.0, FastAPI e SQLite, blindando regras condominiais contra prompt injection e condições de corrida.

---

## Arquitetura

O sistema emprega arquitetura multiagente coordenada pelo Google ADK:

* **AgentePrincipal (Roteador):** Recebe o morador, analisa a intenção da mensagem e realiza a transferência para o especialista adequado. Suas instruções não contêm o texto do regulamento.
* **EspecialistaCondominio (Subagente):** Responsável pelas operações transacionais de reserva, cancelamento e autorização de visitantes via tools conectadas ao banco de dados SQLite.
* **EspecialistaRegulamento (Subagente):** Consulta seletiva de normas internas através de tool dedicada com busca textual cirúrgica por capítulo.

---

## Garantias

### Garantia 1: Cobrança ou Acesso Só com Confirmação
* **Arquivo:** `src/tools/condominio_tools.py` (`reservar_area` e `autorizar_visitante`)
* **Implementação:** Toda reserva para áreas onde `taxa > 0` (salão ou churrasqueira) ou inclusão de visitantes aciona `ctx.request_confirmation(...)`. A execução é interrompida pelo Runner. Mensagens de texto afirmando confirmação são ignoradas; a retomada ocorre exclusivamente quando o endpoint `POST /sessoes/{session_id}/confirmacoes` é acionado. IDs não pendentes retornam `409 Conflict`.

### Garantia 2: Cada Sessão Pertence a um Apartamento
* **Arquivo:** `src/main.py` (`criar_sessao`) e `src/tools/condominio_tools.py`
* **Implementação:** O apartamento é gravado em `session.state["apartamento"]` no `POST /sessoes`. As tools leem o apartamento diretamente do contexto da sessão. O morador pode alegar pertencer a outra unidade no prompt, mas as queries de reserva, cancelamento e consulta utilizam restritamente o apartamento da sessão. A disponibilidade de áreas é verificada de forma booleana sem jamais retornar códigos ou moradores de terceiros.

### Garantia 3: Nada se Perde no Reinício
* **Arquivo:** `src/main.py` (`SQLiteSessionService`) e `src/database.py`
* **Implementação:** A persistência da sessão e seu histórico de eventos são geridos por `SQLiteSessionService("sessoes.db")`. O estado do condomínio é mantido em `condominio.db`. Reiniciar o processo mantém intactos o histórico, o estado da sessão e os eventos.

### Garantia 4: O Regulamento é Consultado, Não Carregado
* **Arquivo:** `src/tools/regulamento_tools.py` (`consultar_regulamento`)
* **Implementação:** O texto integral de `dados/regulamento.md` não reside nas instruções do `AgentePrincipal`. A tool `consultar_regulamento` fatia o documento por seções e retorna unicamente o capítulo temático solicitado, preservando a janela de contexto.

### Garantia 5: Dois Moradores, Uma Reserva (Exclusividade Atômica)
* **Arquivo:** `src/database.py` (`reservas`) e `src/tools/condominio_tools.py`
* **Implementação:** A tabela `reservas` possui a restrição `UNIQUE(area, data)`. Em caso de requisições simultâneas para a mesma data e área, o banco de dados assegura atomicidade com transação `WAL`: a primeira consolida o registro e a segunda dispara `sqlite3.IntegrityError`, tratada na tool com retorno amigável de recusa (HTTP 200).

---

---

---

## Como Rodar

### 1. Configurar Variáveis de Ambiente e Instalação
```bash
# Instalar dependências com uv
uv sync

# Configurar as variáveis de ambiente
cp .env.example .env
# Defina sua chave no .env: GEMINI_API_KEY=sua_chave_aqui
```

### 2. Restauração e Inicialização do Banco de Dados
Restaure as tabelas e a carga inicial do SQLite (condominio.db) a partir dos arquivos JSON:
```bash
uv run python -c "from src.database import init_db; init_db()"
```

### 3. Execução da API
Inicie o servidor Uvicorn:
```bash
uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```
A documentação interativa OpenAPI/Swagger estará em: http://localhost:8000/docs.

### 4. Execução dos Testes Automatizados
Para rodar a suíte completa de testes:
```bash
uv run pytest -v
```
