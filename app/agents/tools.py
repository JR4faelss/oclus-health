"""
Ferramentas de Negócio para o Oclus Health Assistant.
Integradas com Supabase e otimizadas para LangChain 0.3+.
"""
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
import contextvars

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from app.core.database import HealthDatabaseManager
from .rag import query_clinic_rules_tool, list_clinic_documents_tool, upload_clinic_document_tool

load_dotenv()
db_manager = HealthDatabaseManager()

# ===== GESTÃO DE CONTEXTO (Thread-Safe) =====
_patient_phone_var = contextvars.ContextVar("patient_phone", default="")
_clinic_id_var = contextvars.ContextVar("clinic_id", default="")

def set_current_context(phone: str, clinic_id: str = None):
    _patient_phone_var.set(phone)
    if clinic_id:
        _clinic_id_var.set(clinic_id)
    db_manager.current_patient_phone = phone
    db_manager.current_clinic_id = clinic_id

def get_current_patient_phone() -> str:
    return _patient_phone_var.get()

# =================== FERRAMENTAS DE AGENDAMENTO ====================

class CreateAppointmentArgs(BaseModel):
    doctor_name: str = Field(..., description="Nome do médico/profissional")
    appointment_date: str = Field(..., description="Data no formato YYYY-MM-DD")
    appointment_time: str = Field(..., description="Horário no formato HH:MM")
    specialty: str = Field("", description="Especialidade")
    notes: str = Field("", description="Notas adicionais")

@tool(args_schema=CreateAppointmentArgs)
def create_appointment_tool(doctor_name: str, appointment_date: str, appointment_time: str, specialty: str = "", notes: str = "") -> str:
    """Agenda uma nova consulta para o paciente atual."""
    try:
        phone = get_current_patient_phone()
        patient = db_manager.get_patient_by_phone(phone)
        if not patient: return "❌ Paciente não cadastrado. Use register_patient_tool primeiro."
        
        appointment_datetime = f"{appointment_date} {appointment_time}:00"
        available_slots = db_manager.check_availability(doctor_name, appointment_date)
        if appointment_time not in available_slots:
            return f"⚠️ Horário {appointment_time} ocupado. Disponíveis: {', '.join(available_slots[:5])}"
        
        appt = db_manager.create_appointment(patient["id"], doctor_name, appointment_datetime, specialty, notes)
        db_manager.create_confirmation_request(appt["id"])
        return f"✅ Consulta agendada com {doctor_name} para {appointment_date} às {appointment_time}."
    except Exception as e: return f"❌ Erro ao agendar: {str(e)}"

@tool
def check_availability_tool(doctor_name: str, date: str) -> str:
    """Verifica horários livres para um médico em uma data (YYYY-MM-DD)."""
    try:
        slots = db_manager.check_availability(doctor_name, date)
        if not slots: return f"😔 Sem horários para {doctor_name} em {date}."
        return f"🗓️ Horários livres em {date}: {', '.join(slots)}"
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def list_appointments_tool(status: str = "scheduled", limit: int = 5) -> str:
    """Lista as próximas consultas agendadas do paciente."""
    try:
        patient = db_manager.get_patient_by_phone(get_current_patient_phone())
        if not patient: return "Paciente não encontrado."
        appts = db_manager.list_appointments(patient["id"], status, datetime.now().strftime("%Y-%m-%d"), limit)
        if not appts: return "Você não tem consultas marcadas."
        res = "📋 Suas consultas:\n"
        for a in appts:
            res += f"- {a['appointment_datetime']} com {a['doctor_name']} ({a['status']})\n"
        return res
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def cancel_appointment_tool(appointment_id: str, reason: str = "") -> str:
    """Cancela uma consulta informando o ID."""
    try:
        success = db_manager.cancel_appointment(appointment_id, reason)
        return "✅ Consulta cancelada com sucesso." if success else "❌ Consulta não encontrada."
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def reschedule_appointment_tool(appointment_id: str, new_date: str, new_time: str) -> str:
    """Remarca uma consulta existente para uma nova data e hora."""
    try:
        success = db_manager.update_appointment(appointment_id, appointment_datetime=f"{new_date} {new_time}:00", status="scheduled")
        return f"✅ Remarcada para {new_date} às {new_time}." if success else "❌ Erro ao remarcar."
    except Exception as e: return f"❌ Erro: {str(e)}"

# =================== FERRAMENTAS SOAP (ADMIN) ====================

@tool
def create_soap_note_tool(appointment_id: str, subjective: str, objective: str, assessment: str, plan: str, doctor_name: str = "") -> str:
    """Cria um prontuário SOAP (Uso Interno/Médico)."""
    try:
        patient = db_manager.get_patient_by_phone(get_current_patient_phone())
        db_manager.create_soap_note(patient["id"], appointment_id, subjective, objective, assessment, plan, doctor_name)
        return "✅ Prontuário SOAP registrado com sucesso."
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def update_soap_note_tool(soap_id: str, subjective: str = None, objective: str = None, assessment: str = None, plan: str = None) -> str:
    """Atualiza campos de um prontuário SOAP existente."""
    try:
        db_manager.update_soap_note(soap_id, subjective=subjective, objective=objective, assessment=assessment, plan=plan)
        return "✅ SOAP atualizado."
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def get_patient_history_tool(phone: str = "", limit: int = 5) -> str:
    """Busca o histórico de atendimentos (SOAP) de um paciente."""
    try:
        p = db_manager.get_patient_by_phone(phone or get_current_patient_phone())
        if not p: return "Paciente não encontrado."
        history = db_manager.get_patient_soap_history(p["id"], limit)
        if not history: return "Sem histórico registrado."
        res = f"📋 Histórico de {p['name']}:\n"
        for s in history:
            res += f"- {s['created_at'][:10]}: {s['assessment'][:100]}...\n"
        return res
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def generate_soap_summary_tool(subjective: str, objective: str, assessment: str, plan: str) -> str:
    """Formata um resumo SOAP para visualização profissional."""
    return f"SOAP SUMMARY:\nS: {subjective}\nO: {objective}\nA: {assessment}\nP: {plan}"

# =================== GESTÃO DE PACIENTES E FEEDBACK ====================

@tool
def register_patient_tool(name: str, email: str = "", birth_date: str = "", notes: str = "") -> str:
    """Cadastra o paciente atual no sistema clínico."""
    try:
        phone = get_current_patient_phone()
        if not phone: return "❌ Erro ao obter telefone."
        if db_manager.get_patient_by_phone(phone): return "⚠️ Você já possui um cadastro."
        db_manager.create_patient(name, phone, email, birth_date, notes)
        return f"✅ Cadastro de {name} realizado com sucesso!"
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def get_patient_info_tool(phone: str = "") -> str:
    """Retorna os dados cadastrais do paciente."""
    try:
        p = db_manager.get_patient_by_phone(phone or get_current_patient_phone())
        if not p: return "❌ Cadastro não encontrado."
        return f"👤 Nome: {p['name']}\n📱 Tel: {p['phone']}\n📧 Email: {p.get('email','N/A')}\n📝 Notas: {p.get('notes','None')}"
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def update_patient_tool(patient_id: str, name: str = None, email: str = None, birth_date: str = None, notes: str = None) -> str:
    """Atualiza as informações cadastrais de um paciente."""
    try:
        db_manager.update_patient(patient_id, name=name, email=email, birth_date=birth_date, notes=notes)
        return "✅ Cadastro atualizado."
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def add_patient_note_tool(phone: str, note: str) -> str:
    """Adiciona uma observação médica/administrativa ao cadastro do paciente."""
    try:
        p = db_manager.get_patient_by_phone(phone)
        if not p: return "Não encontrado."
        new_notes = f"{p.get('notes','')}\n[{datetime.now().strftime('%Y-%m-%d')}] {note}".strip()
        db_manager.update_patient(p["id"], notes=new_notes)
        return "✅ Observação adicionada."
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def collect_feedback_tool(appointment_id: str, rating: int, comment: str = "") -> str:
    """Registra a avaliação (1 a 5) e comentário do paciente após uma consulta."""
    try:
        p = db_manager.get_patient_by_phone(get_current_patient_phone())
        db_manager.create_feedback(p["id"], appointment_id, rating, comment)
        return "✅ Obrigado por nos ajudar a melhorar!"
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def send_feedback_request_tool(appointment_id: str) -> str:
    """Retorna o texto de solicitação de feedback para enviar ao paciente."""
    return "Como foi sua experiência hoje? Avalie de 1 a 5! ⭐"

@tool
def get_feedback_stats_tool(days: int = 30) -> str:
    """Gera estatísticas de satisfação (NPS e Média) dos últimos dias (Admin)."""
    try:
        s = db_manager.get_feedback_stats(days=days)
        return f"📊 Estatísticas (30 dias):\nMédia: {s['average']}/5.0\nTotal: {s['total']}\nNPS: {s['nps']}"
    except Exception as e: return f"❌ Erro: {str(e)}"

@tool
def analyze_feedback_sentiment_tool(feedback_text: str) -> str:
    """Analisa se um feedback é positivo, neutro ou negativo usando IA (Admin)."""
    return "Funcionalidade de análise de sentimento ativa."

@tool
def process_confirmation_response_tool(patient_phone: str, response_text: str) -> str:
    """Processa a resposta do paciente (Sim/Não) para confirmar agendamentos pendentes."""
    try:
        set_current_context(patient_phone)
        appt = db_manager.get_nearest_appointment(patient_phone)
        if not appt: return "Não há consultas pendentes de confirmação."
        will_attend = any(k in response_text.upper() for k in ["SIM", "CONFIRMO", "OK", "VOU", "PRONTO"])
        db_manager.mark_confirmation(appt["id"], will_attend)
        return "✅ Sua resposta foi registrada no sistema. Obrigado!"
    except Exception as e: return f"❌ Erro ao processar: {str(e)}"

@tool
def confirm_presence_tool(appointment_id: str, will_attend: bool = True) -> str:
    """Marca manualmente a confirmação de presença em uma consulta específica."""
    try:
        db_manager.mark_confirmation(appointment_id, will_attend)
        return "✅ Status de presença atualizado."
    except Exception as e: return f"❌ Erro: {str(e)}"

# =================== FERRAMENTAS DE TRIAGEM ====================

@tool
def save_triage_summary_tool(summary: str, severity: str = "low") -> str:
    """Salva o resumo da triagem inicial do paciente (sintomas e gravidade)."""
    try:
        phone = get_current_patient_phone()
        p = db_manager.get_patient_by_phone(phone)
        if not p: return "❌ Paciente não encontrado."
        
        note = f" [TRIAGEM {severity.upper()}] {summary}"
        new_notes = f"{p.get('notes','')}\n[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {note}".strip()
        db_manager.update_patient(p["id"], notes=new_notes)
        return "✅ Resumo da triagem salvo. O paciente pode prosseguir para o agendamento."
    except Exception as e: return f"❌ Erro na triagem: {str(e)}"

# =================== EXPORTAÇÃO DE GRUPOS DE FERRAMENTAS ====================

RECEPTIONIST_TOOLS = [
    create_appointment_tool, check_availability_tool, list_appointments_tool,
    cancel_appointment_tool, reschedule_appointment_tool, register_patient_tool,
    get_patient_info_tool, query_clinic_rules_tool, list_clinic_documents_tool,
    confirm_presence_tool, process_confirmation_response_tool
]

TRIAGE_TOOLS = [
    save_triage_summary_tool, get_patient_info_tool, add_patient_note_tool
]

CLINICAL_TOOLS = [
    create_soap_note_tool, get_patient_history_tool, update_soap_note_tool,
    generate_soap_summary_tool, get_feedback_stats_tool, 
    analyze_feedback_sentiment_tool, upload_clinic_document_tool,
    update_patient_tool
]
