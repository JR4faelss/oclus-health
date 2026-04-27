import requests
import json
import time
import threading

# Configurações do ambiente de teste
BASE_URL = "http://localhost:3001"
ADMIN_TOKEN = "oclus-admin-secret-123" # Defina o mesmo do seu .env

def test_health_check():
    print("🔍 Testando Health Check...")
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        print(f"✅ Status: {response.status_code} - {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Erro ao conectar na API: {e}")
        return False

def test_admin_security():
    print("\n🛡️ Testando Segurança Admin...")
    # Teste sem token
    res_no_token = requests.get(f"{BASE_URL}/api/admin/stats")
    print(f"Bloqueio sem token: {'✅ Passou (401)' if res_no_token.status_code == 401 else '❌ Falhou'}")
    
    # Teste com token correto
    headers = {"X-Admin-Token": ADMIN_TOKEN}
    res_with_token = requests.get(f"{BASE_URL}/api/admin/stats", headers=headers)
    print(f"Acesso com token: {'✅ Passou (200)' if res_with_token.status_code == 200 else '❌ Falhou'}")

def simulate_patient_chat(phone, message, name):
    """Simula o envio de uma mensagem pelo webhook (como o WAHA faria)"""
    payload = {
        "event": "message",
        "payload": {
            "from": f"{phone}@c.us",
            "body": message,
            "fromMe": False
        }
    }
    print(f"📩 [{name}] Enviando: {message}")
    response = requests.post(f"{BASE_URL}/api/webhook", json=payload)
    return response.status_code == 200

def test_session_isolation():
    print("\n👥 Testando Isolamento de Sessões (LGPD)...")
    
    # Paciente A se identifica
    simulate_patient_chat("5511999991111", "Olá, meu nome é João Silva.", "JOÃO")
    time.sleep(1)
    
    # Paciente B se identifica com outro nome
    simulate_patient_chat("5511888882222", "Oi, aqui é a Maria Oliveira.", "MARIA")
    time.sleep(1)
    
    # Pergunta cruzada: João pergunta quem ele é
    print("🤔 Verificando se o agente lembra o nome correto para cada um...")
    simulate_patient_chat("5511999991111", "Qual é o meu nome?", "JOÃO")
    simulate_patient_chat("5511888882222", "Qual é o meu nome?", "MARIA")
    
    print("\n💡 Verifique os logs do servidor para confirmar que o Agente respondeu 'João' para um e 'Maria' para outro.")

def test_rag_knowledge():
    print("\n📚 Testando Conhecimento da Clínica (RAG)...")
    # Pergunta algo que deve estar nos documentos da clínica
    simulate_patient_chat("5511999991111", "Quais são os horários de funcionamento da clínica?", "JOÃO")

if __name__ == "__main__":
    print("🚀 Iniciando Testes do Oclus Health Assistant\n")
    
    if test_health_check():
        test_admin_security()
        
        # Rodar testes de chat
        # Nota: Certifique-se que o servidor Flask está rodando em outro terminal
        test_session_isolation()
        test_rag_knowledge()
        
        print("\n✨ Testes finalizados! Verifique as respostas no terminal onde o servidor está rodando.")
    else:
        print("\n❌ Abortando: Servidor não está respondendo em localhost:3001")
