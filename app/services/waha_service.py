import requests
import os
from dotenv import load_dotenv

load_dotenv()

class WahaService:
    """
    Serviço para integração com a API WAHA (WhatsApp HTTP API).
    """
    
    def __init__(self):
        # Configurações via variáveis de ambiente para segurança
        self.api_key = os.getenv("WHATSAPP_API_KEY")
        self.base_url = os.getenv("WHATSAPP_API_URL", "http://localhost:3000")
        self.session = os.getenv("WHATSAPP_INSTANCE_NAME", "oclus_health")
        
        if not self.api_key:
            print("⚠️ Aviso: WHATSAPP_API_KEY não configurada no .env")
            
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        
    def _get_chat_id(self, phone):
        """Formata o telefone para o padrão do WAHA (suporta @c.us e @lid)"""
        if not phone:
            return ""
        str_phone = str(phone)
        if "@c.us" in str_phone or "@lid" in str_phone:
            return str_phone
        # Remove caracteres não numéricos para números puros
        clean_phone = ''.join(filter(str.isdigit, str_phone))
        return f"{clean_phone}@c.us"

    def _post(self, endpoint, payload):
        """Método auxiliar para requisições POST com tratamento de erro detalhado."""
        url = f"{self.base_url}/api/{endpoint}"
        try:
            response = requests.post(url, json=payload, headers=self.headers, timeout=10)
            if response.status_code not in [200, 201]:
                print(f"❌ Erro WAHA ({endpoint}) - Status {response.status_code}: {response.text}")
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Erro de conexão WAHA ({endpoint}): {e}")
            return None

    def start_typing(self, phone):
        """Simula que o agente está digitando."""
        chat_id = self._get_chat_id(phone)
        payload = {"chatId": chat_id, "session": self.session}
        return self._post("startTyping", payload)

    def stop_typing(self, phone):
        """Para a simulação de digitação."""
        chat_id = self._get_chat_id(phone)
        payload = {"chatId": chat_id, "session": self.session}
        return self._post("stopTyping", payload)

    def send_message(self, phone, message, reply_to_id=None):
        """Envia mensagem de texto via WhatsApp."""
        chat_id = self._get_chat_id(phone)
        payload = {
            "chatId": chat_id,
            "text": message,
            "session": self.session
        }
        
        if reply_to_id:
            payload["reply_to"] = reply_to_id

        response = self._post("sendText", payload)
        return response and response.status_code in [200, 201]
