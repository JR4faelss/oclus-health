import schedule
import time
import threading
import logging
from .database import HealthDatabaseManager
from datetime import datetime
from dotenv import load_dotenv
import os
from app.services.waha_service import WahaService
import random

# Configuração de Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ConfirmationScheduler")

load_dotenv()
db_manager = HealthDatabaseManager()
waha = WahaService()

# Configurações
CONFIRMATION_ENABLED = os.getenv("CONFIRMATION_ENABLED", "true").lower() == "true"

def send_confirmation_reminders():
    """
    Envia lembretes de confirmação para consultas nas próximas 24h.
    """
    if not CONFIRMATION_ENABLED:
        logger.info("Confirmações desativadas (CONFIRMATION_ENABLED=false)")
        return
    
    try:
        logger.info("Verificando consultas para confirmação (janela de 24h)...")
        
        # Buscar consultas pendentes (24h antes)
        try:
            pending = db_manager.list_pending_confirmations(hours_ahead=24)
        except Exception as e:
            logger.error(f"❌ Erro ao conectar no SUPABASE: {e}. Verifique SUPABASE_URL no .env")
            return
        
        if not pending:
            logger.info("Nenhuma consulta pendente encontrada.")
            return
        
        logger.info(f"Processando {len(pending)} consultas potenciais.")
        
        for appointment in pending:
            try:
                appt_id = appointment['id']
                
                # 1. Verificar/Criar registro de confirmação com segurança
                existing = db_manager.supabase.table("confirmations").select("*").eq(
                    "appointment_id", appt_id
                ).execute()
                
                conf_data = existing.data[0] if existing.data else None
                
                if not conf_data:
                    # Cria novo registro se não existir
                    conf_data = db_manager.create_confirmation_request(appt_id)
                    logger.info(f"Novo registro de confirmação criado para consulta {appt_id[:8]}")
                
                # 2. Verificar se o lembrete já foi enviado
                if conf_data.get("reminder_sent_at"):
                    continue
                
                # 3. Extrair dados do paciente
                patient = appointment.get("patients", {})
                patient_name = patient.get("name", "Paciente")
                patient_phone = patient.get("phone", "")
                
                if not patient_phone:
                    logger.warning(f"Consulta {appt_id[:8]} sem telefone válido.")
                    continue
                
                # 4. Formatar data e hora
                try:
                    appt_dt = datetime.fromisoformat(appointment["appointment_datetime"].replace('Z', ''))
                    date_str = appt_dt.strftime("%d/%m/%Y")
                    time_str = appt_dt.strftime("%H:%M")
                except Exception as e:
                    logger.error(f"Erro ao formatar data da consulta {appt_id[:8]}: {e}")
                    continue
                
                # 5. Montar e enviar mensagem
                message = f"""🏥 *Lembrete de Consulta*

Olá, {patient_name}!

Você tem uma consulta agendada para:
📅 *Data:* {date_str}
🕐 *Horário:* {time_str}
👨‍⚕️ *Profissional:* {appointment.get('doctor_name', 'N/A')}

Por favor, confirme sua presença respondendo:
✅ *CONFIRMO* - se você vai comparecer
❌ *NÃO VOU* - se precisar remarcar

Aguardamos seu retorno! 😊"""
                
                if waha.send_message(patient_phone, message.strip()):
                    # Atualizar status no banco
                    db_manager.supabase.table("confirmations").update({
                        "reminder_sent_at": datetime.now().isoformat()
                    }).eq("appointment_id", appt_id).execute()
                    
                    logger.info(f"✅ Lembrete 24h enviado: {patient_name} ({patient_phone})")
                else:
                    logger.error(f"❌ Falha ao enviar lembrete para {patient_phone}")
                
                # Delay aleatório para evitar bloqueio por spam (Anti-ban)
                time.sleep(random.randint(5, 15))
                
            except Exception as e:
                logger.error(f"Erro ao processar consulta {appointment.get('id', 'unknown')}: {e}")
                continue
                
    except Exception as e:
        logger.error(f"Erro fatal no scheduler de confirmações: {e}")

def send_2h_reminder():
    """
    Envia lembrete final 2h antes para consultas já confirmadas.
    """
    if not CONFIRMATION_ENABLED:
        return
    
    try:
        logger.info("Verificando lembretes de última hora (janela de 2h)...")
        pending = db_manager.list_pending_confirmations(hours_ahead=2)
        confirmed = [a for a in pending if a.get("status") == "confirmed"]
        
        for appointment in confirmed:
            try:
                appt_id = appointment['id']
                patient = appointment.get("patients", {})
                patient_phone = patient.get("phone")
                
                if not patient_phone: continue

                # Verificar se já enviou o lembrete de 2h
                check = db_manager.supabase.table("confirmations").select("reminder_2h_sent_at").eq(
                    "appointment_id", appt_id
                ).execute()
                
                if check.data and check.data[0].get("reminder_2h_sent_at"):
                    continue

                appt_dt = datetime.fromisoformat(appointment["appointment_datetime"].replace('Z', ''))
                message = f"⏰ *Lembrete:* Sua consulta é hoje às {appt_dt.strftime('%H:%M')}. Nos vemos em breve! 👋"
                
                if waha.send_message(patient_phone, message):
                    db_manager.supabase.table("confirmations").update({
                        "reminder_2h_sent_at": datetime.now().isoformat()
                    }).eq("appointment_id", appt_id).execute()
                    logger.info(f"✅ Lembrete 2h enviado para {patient_phone}")
                
                time.sleep(2)
            except Exception as e:
                logger.error(f"Erro no lembrete 2h: {e}")
    except Exception as e:
        logger.error(f"Erro no scheduler 2h: {e}")

def run_scheduler():
    """Loop principal do scheduler."""
    logger.info("🔔 Iniciando loop do Scheduler de Confirmações...")
    
    # Agendamentos
    schedule.every(1).hours.do(send_confirmation_reminders)
    schedule.every(30).minutes.do(send_2h_reminder)
    
    # Execução imediata ao iniciar
    send_confirmation_reminders()
    
    while True:
        schedule.run_pending()
        time.sleep(30)

def run_scheduler_background():
    """Inicia em thread separada para uso com Flask."""
    thread = threading.Thread(target=run_scheduler, daemon=True)
    thread.start()
    return thread

if __name__ == "__main__":
    run_scheduler()
