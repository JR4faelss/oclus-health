"""
Oclus Health Agent - Arquitetura Multiagente LangGraph.
Implementa o padrão Supervisor para orquestrar agentes especialistas.
"""
import operator
import logging
from typing import Annotated, List, Sequence, TypedDict, Union, Literal
from datetime import datetime
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

# Importar ferramentas e utilitários
from .tools import (
    RECEPTIONIST_TOOLS, TRIAGE_TOOLS, CLINICAL_TOOLS,
    set_current_context, db_manager
)
from app.utils.media_parser import process_multimodal_input

load_dotenv()
logger = logging.getLogger("OclusMultiAgent")

# --- DEFINIÇÃO DO ESTADO ---
class AgentState(TypedDict):
    # O operador 'operator.add' permite que as mensagens sejam acumuladas no histórico
    messages: Annotated[Sequence[BaseMessage], operator.add]
    next: str  # Próximo agente a ser chamado

# --- AGENTE SUPERVISOR ---
def create_supervisor(llm: ChatOpenAI, agents: List[str]):
    options = ["FINISH"] + agents
    system_prompt = (
        "Você é o Supervisor da clínica Oclus Health. Sua tarefa é gerenciar o fluxo de conversa.\n"
        "REGRAS CRÍTICAS:\n"
        "1. Se o usuário apenas disse algo que não exige ferramentas, use 'Recepcionista' e depois 'FINISH'.\n"
        "2. Se um agente especialista (ex: Recepcionista) já respondeu que NÃO encontrou uma informação ou que houve um erro, NÃO peça para ele tentar novamente. Escolha 'FINISH'.\n"
        "3. Evite loops: Se a última mensagem do histórico já for uma resposta conclusiva ou um pedido de desculpas por falta de informação, encerre com 'FINISH'.\n"
        "4. Use 'Recepcionista' para agendamentos/preços, 'Triagem' para sintomas e 'Clinico' para prontuários.\n"
        "\nResponda APENAS com o nome do próximo agente ou 'FINISH'."
    )
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        MessagesPlaceholder(variable_name="messages"),
        (
            "system",
            "Dada a conversa acima, quem deve agir a seguir? Se a dúvida já foi respondida ou a informação é inexistente, escolha 'FINISH'."
            " Escolha um de: {options}",
        ),
    ]).partial(options=str(options), agents=", ".join(agents))
    
    return prompt | llm.with_structured_output(TypedDict("Route", {"next": Literal["Recepcionista", "Triagem", "Clinico", "FINISH"]}))

# --- CLASSE PRINCIPAL ---
class OclusHealthAgent:
    def __init__(self, clinic_id: str = "default"):
        self.clinic_id = clinic_id
        self.llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # 1. Criar Agentes Especialistas com Prompts Enriquecidos
        receptionist_agent = create_react_agent(
            self.llm, RECEPTIONIST_TOOLS,
            state_modifier=SystemMessage(content=(
                "Você é a Recepcionista da Oclus Health.\n"
                "DIRETRIZES DE RAG E SEGURANÇA:\n"
                "1. Se você usar a ferramenta de consulta (query_clinic_rules_tool) e ela retornar que não há informações ou der erro, aceite esse resultado.\n"
                "2. FALLBACK: Se a informação não estiver na base, responda: 'Lamento, mas ainda não tenho essa informação específica no meu manual. Posso tentar ajudar com outra coisa ou encaminhar para um atendente humano?'.\n"
                "3. NUNCA tente chamar a mesma ferramenta com a mesma pergunta mais de uma vez se ela falhou.\n"
                "4. Mantenha um tom profissional e acolhedor."
            ))
        )
        triage_agent = create_react_agent(
            self.llm, TRIAGE_TOOLS,
            state_modifier=SystemMessage(content=(
                "Você é o Especialista de Triagem da Oclus Health. Sua missão é ouvir o paciente com máxima empatia "
                "e coletar informações cruciais sobre o estado de saúde dele antes da consulta.\n\n"
                "COMO ATUAR:\n"
                "1. Pergunte sobre os sintomas principais e há quanto tempo começaram.\n"
                "2. Verifique se há sinais de alerta (dores intensas, febre alta, falta de ar).\n"
                "3. Mantenha a calma do paciente, mas seja direto na coleta de dados.\n"
                "4. CRÍTICO: Antes de finalizar a triagem e passar para o agendamento, você DEVE obrigatoriamente "
                "usar a ferramenta 'save_triage_summary_tool' para registrar o resumo no sistema."
            ))
        )
        clinical_agent = create_react_agent(
            self.llm, CLINICAL_TOOLS,
            state_modifier=SystemMessage(content=(
                "Você é o Assistente Clínico Sênior da Oclus Health. Seu foco é a organização técnica do prontuário e o histórico médico.\n\n"
                "RESPONSABILIDADES:\n"
                "1. Auxiliar médicos na criação e consulta de prontuários no padrão SOAP.\n"
                "2. Resumir o histórico do paciente quando solicitado por um profissional de saúde.\n"
                "3. Analisar feedbacks e estatísticas de atendimento.\n\n"
                "TOM DE VOZ: Extremamente profissional, preciso e seguro. Use terminologia médica adequada, mas seja acessível se estiver falando com o paciente sobre seu próprio histórico."
            ))
        )

        # 2. Funções de Nó (Nodes)
        def call_receptionist(state):
            response = receptionist_agent.invoke(state)
            return {"messages": [response["messages"][-1]]}

        def call_triage(state):
            response = triage_agent.invoke(state)
            return {"messages": [response["messages"][-1]]}

        def call_clinical(state):
            response = clinical_agent.invoke(state)
            return {"messages": [response["messages"][-1]]}

        # 3. Construir o Grafo
        workflow = StateGraph(AgentState)
        
        # Adicionar Nós
        workflow.add_node("Recepcionista", call_receptionist)
        workflow.add_node("Triagem", call_triage)
        workflow.add_node("Clinico", call_clinical)
        
        supervisor_node = create_supervisor(self.llm, ["Recepcionista", "Triagem", "Clinico"])
        workflow.add_node("supervisor", lambda state: supervisor_node.invoke(state))

        # Configurar Arestas (Edges)
        for agent in ["Recepcionista", "Triagem", "Clinico"]:
            # Após um especialista agir, ele volta para o supervisor
            workflow.add_edge(agent, "supervisor")

        # Roteamento condicional do supervisor
        conditional_map = {k: k for k in ["Recepcionista", "Triagem", "Clinico"]}
        conditional_map["FINISH"] = END
        
        workflow.add_conditional_edges("supervisor", lambda x: x["next"], conditional_map)
        
        workflow.set_entry_point("supervisor")
        
        self.memory = MemorySaver()
        self.graph = workflow.compile(checkpointer=self.memory)

    def process_message(self, message: str, patient_phone: str, audio_path: str = None, image_path: str = None) -> str:
        """Processa mensagens com suporte multimodal e multiagente."""
        try:
            set_current_context(patient_phone, self.clinic_id)
            
            # Injetar data atual para evitar alucinações de calendário
            current_time = datetime.now().strftime("%A, %d de %B de %Y, às %H:%M")
            time_context = f"\n\n[CONTEXTO TEMPORAL]: Hoje é {current_time}. Considere esta data para agendamentos."
            
            # Processar entrada multimodal se existir
            multimodal_context = process_multimodal_input(audio_path, image_path)
            full_content = f"{message}{time_context}\n\n{multimodal_context}".strip()
            
            config = {"configurable": {"thread_id": patient_phone}, "recursion_limit": 10}
            
            # Executar o grafo
            result = self.graph.invoke(
                {"messages": [HumanMessage(content=full_content)]},
                config
            )
            
            return result["messages"][-1].content
            
        except Exception as e:
            logger.error(f"Erro no Grafo Multiagente ({patient_phone}): {e}")
            return "Sinto muito, tive um erro técnico ao processar sua solicitação."

# Singleton Factory
_agent_instance = None
def get_agent(clinic_id: str = "default") -> OclusHealthAgent:
    global _agent_instance
    if _agent_instance is None:
        _agent_instance = OclusHealthAgent(clinic_id=clinic_id)
    return _agent_instance
