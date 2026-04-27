"""
Gerenciador de banco de dados Supabase para Oclus Health Assistant.
Organiza para onde cada informação deve ser armazenada no Banco de Dados.
Gerencia: clínicas, pacientes, consultas, prontuários SOAP, feedbacks.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import os
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()


class HealthDatabaseManager:
    """Gerenciador de banco de dados para sistema de saúde."""
    
    def __init__(self):
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL e SUPABASE_SERVICE_ROLE_KEY devem estar no .env")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        self.current_clinic_id = None  # Será definido pelo contexto
        self.current_patient_phone = None
    
    # ==================== HELPER FUNCTIONS ====================
    def _clean_phone(self, phone: Optional[str]) -> str:
        """Normaliza telefone mantendo apenas dígitos."""
        if not phone:
            return ""
        return ''.join(ch for ch in str(phone) if ch.isdigit())
    
    # ==================== PACIENTES ====================
    def create_patient(self, name: str, phone: str, email: str = "", 
                      birth_date: str = "", notes: str = "", clinic_id: str = None) -> Dict:
        """Cadastra novo paciente."""
        clean_phone = self._clean_phone(phone)
        data = {
            "name": name,
            "phone": clean_phone,
            "email": email,
            "birth_date": birth_date or None,
            "notes": notes,
            "clinic_id": clinic_id or self.current_clinic_id,
            "created_at": datetime.now().isoformat()
        }
        result = self.supabase.table("patients").insert(data).execute()
        return result.data[0] if result.data else {}
    
    def get_patient_by_phone(self, phone: str) -> Optional[Dict]:
        """Busca paciente por telefone de forma robusta."""
        try:
            clean_phone = self._clean_phone(phone)
            if not clean_phone: return None
            
            result = self.supabase.table("patients").select("*").eq("phone", clean_phone).execute()
            if result.data and len(result.data) > 0:
                return result.data[0]
            return None
        except Exception as e:
            print(f"⚠️ Erro ao buscar paciente: {e}")
            return None
    
    def update_patient(self, patient_id: str, **kwargs) -> Dict:
        """Atualiza dados do paciente."""
        result = self.supabase.table("patients").update(kwargs).eq("id", patient_id).execute()
        return result.data[0] if result.data else {}
    
    # ==================== CONSULTAS ====================
    def create_appointment(self, patient_id: str, doctor_name: str, 
                          appointment_datetime: str, specialty: str = "",
                          notes: str = "", clinic_id: str = None) -> Dict:
        """Cria nova consulta."""
        data = {
            "patient_id": patient_id,
            "doctor_name": doctor_name,
            "appointment_datetime": appointment_datetime,
            "specialty": specialty,
            "status": "scheduled",  # scheduled, confirmed, completed, cancelled, no_show
            "notes": notes,
            "clinic_id": clinic_id or self.current_clinic_id,
            "created_at": datetime.now().isoformat()
        }
        result = self.supabase.table("appointments").insert(data).execute()
        return result.data[0] if result.data else {}
    
    def list_appointments(self, patient_id: str = None, status: str = None, 
                         date_from: str = None, limit: int = 50) -> List[Dict]:
        """Lista consultas com filtros."""
        query = self.supabase.table("appointments").select("*, patients(name, phone)")
        
        if patient_id:
            query = query.eq("patient_id", patient_id)
        if status:
            query = query.eq("status", status)
        if date_from:
            query = query.gte("appointment_datetime", date_from)
        
        query = query.order("appointment_datetime", desc=False).limit(limit)
        result = query.execute()
        return result.data if result.data else []
    
    def update_appointment(self, appointment_id: str, **kwargs) -> Dict:
        """Atualiza consulta."""
        result = self.supabase.table("appointments").update(kwargs).eq("id", appointment_id).execute()
        return result.data[0] if result.data else {}
    
    def get_appointment(self, appointment_id: str) -> Dict:
        """Retorna detalhes de uma consulta específica."""
        result = self.supabase.table("appointments").select("*").eq("id", appointment_id).execute()
        return result.data[0] if result.data else {}
    
    def cancel_appointment(self, appointment_id: str, reason: str = "") -> Dict:
        """Cancela consulta."""
        data = {"status": "cancelled", "cancellation_reason": reason}
        return self.update_appointment(appointment_id, **data)
    
    def check_availability(self, doctor_name: str, date: str, clinic_id: str = None) -> List[str]:
        """
        Verifica horários disponíveis para um médico em uma data.
        Retorna lista de horários livres.
        """
        # Buscar consultas agendadas para o médico nessa data
        start_date = f"{date} 00:00:00"
        end_date = f"{date} 23:59:59"
        
        query = self.supabase.table("appointments").select("appointment_datetime")
        query = query.eq("doctor_name", doctor_name)
        query = query.gte("appointment_datetime", start_date)
        query = query.lte("appointment_datetime", end_date)
        query = query.neq("status", "cancelled")
        
        result = query.execute()
        booked_times = [appt["appointment_datetime"][:16] for appt in (result.data or [])]
        
        # Gerar horários possíveis (8h às 18h, intervalos de 30min)
        from datetime import datetime, timedelta
        working_start = datetime.strptime(f"{date} 08:00", "%Y-%m-%d %H:%M")
        working_end = datetime.strptime(f"{date} 18:00", "%Y-%m-%d %H:%M")
        duration = timedelta(minutes=30)
        
        available_slots = []
        current = working_start
        while current < working_end:
            time_str = current.strftime("%Y-%m-%d %H:%M")
            if time_str not in booked_times:
                available_slots.append(current.strftime("%H:%M"))
            current += duration
        
        return available_slots
    
    # ==================== PRONTUÁRIOS SOAP ====================
    def create_soap_note(self, patient_id: str, appointment_id: str,
                        subjective: str, objective: str, assessment: str, 
                        plan: str, doctor_name: str = "") -> Dict:
        """Cria prontuário usando metodologia SOAP."""
        data = {
            "patient_id": patient_id,
            "appointment_id": appointment_id,
            "subjective": subjective,  # Queixa do paciente
            "objective": objective,    # Observações clínicas
            "assessment": assessment,  # Avaliação/Diagnóstico
            "plan": plan,             # Plano de tratamento
            "doctor_name": doctor_name,
            "created_at": datetime.now().isoformat()
        }
        result = self.supabase.table("soap_notes").insert(data).execute()
        return result.data[0] if result.data else {}
    
    def get_patient_soap_history(self, patient_id: str, limit: int = 10) -> List[Dict]:
        """Retorna histórico de prontuários SOAP do paciente."""
        query = self.supabase.table("soap_notes").select("*")
        query = query.eq("patient_id", patient_id)
        query = query.order("created_at", desc=True).limit(limit)
        result = query.execute()
        return result.data if result.data else []
    
    def update_soap_note(self, soap_id: str, **kwargs) -> Dict:
        """Atualiza prontuário SOAP."""
        result = self.supabase.table("soap_notes").update(kwargs).eq("id", soap_id).execute()
        return result.data[0] if result.data else {}

    def list_soap_notes(self, limit: int = 50, clinic_id: str = None) -> List[Dict]:
        """Lista prontuários SOAP com detalhes do paciente."""
        query = self.supabase.table("soap_notes").select("*, patients(name, phone)")
        if clinic_id or self.current_clinic_id:
            # Assumindo que patients tem clinic_id para filtrar ou soap_notes tem clinic_id
            # Se soap_notes não tiver clinic_id, filtramos via patients join
            pass
        
        query = query.order("created_at", desc=True).limit(limit)
        result = query.execute()
        return result.data if result.data else []

    def sign_soap_note(self, soap_id: str) -> Dict:
        """Marca um prontuário como assinado."""
        return self.update_soap_note(soap_id, signed=True)
    
    # ==================== CONFIRMAÇÕES ====================
    def create_confirmation_request(self, appointment_id: str) -> Dict:
        """Cria solicitação de confirmação."""
        data = {
            "appointment_id": appointment_id,
            "status": "pending",  # pending, confirmed, declined
            "sent_at": datetime.now().isoformat()
        }
        result = self.supabase.table("confirmations").insert(data).execute()
        return result.data[0] if result.data else {}
    
    def mark_confirmation(self, appointment_id: str, confirmed: bool) -> Dict:
        """Marca confirmação de presença."""
        status = "confirmed" if confirmed else "declined"
        
        # Atualizar tabela confirmations
        self.supabase.table("confirmations").update({
            "status": status,
            "confirmed_at": datetime.now().isoformat()
        }).eq("appointment_id", appointment_id).execute()
        
        # Atualizar status da consulta
        new_status = "confirmed" if confirmed else "cancelled"
        return self.update_appointment(appointment_id, status=new_status)
    
    def list_pending_confirmations(self, hours_ahead: int = 24) -> List[Dict]:
        """Lista consultas que precisam de confirmação."""
        now = datetime.now()
        target_time = now + timedelta(hours=hours_ahead)
        
        # Buscar consultas scheduled entre agora e o target_time
        query = self.supabase.table("appointments").select("*, patients(name, phone)")
        query = query.eq("status", "scheduled")
        query = query.gte("appointment_datetime", now.isoformat())
        query = query.lte("appointment_datetime", target_time.isoformat())
        
        result = query.execute()
        return result.data if result.data else []
    
    def get_nearest_appointment(self, patient_phone: str) -> Optional[Dict]:
        """Retorna a próxima consulta agendada do paciente."""
        clean_phone = self._clean_phone(patient_phone)
        now = datetime.now()
        
        query = self.supabase.table("appointments").select("*, patients(name, phone)")
        query = query.eq("patients.phone", clean_phone)
        query = query.eq("status", "scheduled")
        query = query.gte("appointment_datetime", now.isoformat())
        query = query.order("appointment_datetime", desc=False).limit(1)
        
        result = query.execute()
        return result.data[0] if result.data else None
    
    # ==================== FEEDBACK ====================
    def create_feedback(self, patient_id: str, appointment_id: str,
                       rating: int, comment: str = "") -> Dict:
        """Registra feedback do paciente."""
        data = {
            "patient_id": patient_id,
            "appointment_id": appointment_id,
            "rating": rating,  # 1-5
            "comment": comment,
            "created_at": datetime.now().isoformat()
        }
        result = self.supabase.table("feedbacks").insert(data).execute()
        return result.data[0] if result.data else {}
    
    def get_feedback_stats(self, days: int = 30) -> Dict:
        """Estatísticas de feedback (removido filtro de clinic_id)."""
        from_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        try:
            query = self.supabase.table("feedbacks").select("rating")
            query = query.gte("created_at", from_date)
            
            result = query.execute()
            feedbacks = result.data if result.data else []
            
            if not feedbacks:
                return {"average": 0, "total": 0, "nps": 0}
            
            ratings = [f["rating"] for f in feedbacks]
            avg_rating = sum(ratings) / len(ratings)
            
            # Calcular NPS (detratores 1-3, passivos 4, promotores 5)
            promoters = len([r for r in ratings if r == 5])
            detractors = len([r for r in ratings if r <= 3])
            nps = ((promoters - detractors) / len(ratings)) * 100
            
            return {
                "average": round(avg_rating, 2),
                "total": len(ratings),
                "nps": round(nps, 2)
            }
        except Exception:
            return {"average": 0, "total": 0, "nps": 0}
    
    # ==================== DOCUMENTOS (Metadados para RAG) ====================
    def register_document(self, filename: str, document_type: str, 
                         file_path: str, clinic_id: str = "default") -> Dict:
        """Registra metadados de documento carregado para RAG."""
        data = {
            "filename": filename,
            "document_type": document_type,  # rules, procedures, protocols, faq
            "file_path": file_path,
            "clinic_id": clinic_id,
            "uploaded_at": datetime.now().isoformat()
        }
        result = self.supabase.table("documents").insert(data).execute()
        return result.data[0] if result.data else {}
    
    def list_documents(self) -> List[Dict]:
        """Lista documentos registrados (removido filtro de clinic_id)."""
        try:
            query = self.supabase.table("documents").select("*")
            result = query.execute()
            return result.data if result.data else []
        except Exception:
            return []
