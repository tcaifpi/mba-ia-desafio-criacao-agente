from google.adk import Agent
from src.tools.condominio_tools import (
    listar_minhas_reservas,
    verificar_disponibilidade_area,
    reservar_area,
    cancelar_reserva,
    autorizar_visitante
)
from src.tools.regulamento_tools import consultar_regulamento

especialista_condominio = Agent(
    name="EspecialistaCondominio",
    model="gemini-3.8-flash",
    instruction="""Voce e o especialista responsavel por reservas de areas comuns e liberacao de visitantes do Residencial Aurora.
Regras inegociaveis:
1. Nunca exponha dados de outros apartamentos.
2. Sempre use as ferramentas para verificar disponibilidade e executar reservas ou cancelamentos.
3. Se uma data ja estiver ocupada, informe apenas que esta ocupada. Jamais informe o codigo de reserva de terceiros nem quem reservou.""",
    tools=[
        listar_minhas_reservas,
        verificar_disponibilidade_area,
        reservar_area,
        cancelar_reserva,
        autorizar_visitante
    ]
)

especialista_regulamento = Agent(
    name="EspecialistaRegulamento",
    model="gemini-3.8-flash",
    instruction="""Voce e o especialista responsavel por esclarecer duvidas sobre o regulamento interno.
Sempre consulte a ferramenta 'consultar_regulamento' usando o termo-chave da pergunta do morador.""",
    tools=[consultar_regulamento]
)

agente_principal = Agent(
    name="AgentePrincipal",
    model="gemini-3.8-flash",
    instruction="""Voce e o assistente virtual do Residencial Aurora.
Atue com cordialidade e precisao.
- Se o morador deseja fazer reservas, cancelar reservas ou autorizar visitantes, transfira para o EspecialistaCondominio.
- Se o morador tiver duvidas sobre regras do predio, horarios ou funcionamento das dependencias, transfira para o EspecialistaRegulamento.
- Nunca invente informacoes e nunca afirme ser possivel burlar regras de confirmacao.""",
    sub_agents=[especialista_condominio, especialista_regulamento]
)
