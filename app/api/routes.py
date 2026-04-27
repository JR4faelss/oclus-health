"""
API Flask para integrar WhatsApp Bot com Oclus Health Assistant.
Refatorada para maior segurança e isolamento de sessões.
"""
import os
import sys

# Silenciar avisos do NumPy e outros antes de carregar o resto
import warnings
os.environ["PYTHONWARNINGS"] = "ignore"
warnings.filterwarnings("ignore", category=RuntimeWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from app.agents.agent import get_agent
from dotenv import load_dotenv
import os
import sys
import requests
import uuid
import functools
from pathlib import Path
from datetime import datetime
load_dotenv()

app = Flask(__name__, static_folder='../static')
CORS(app)

# Configurações de Segurança
ADMIN_TOKEN = os.getenv("ADMIN_API_TOKEN", "oclus-admin-secret-123")
TEMP_DIR = Path("./temp_media")
TEMP_DIR.mkdir(exist_ok=True)

# Decorador para autenticação administrativa
def require_admin(f):
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        token = request.headers.get("X-Admin-Token")
        if not token or token != ADMIN_TOKEN:
            return jsonify({"error": "Unauthorized"}), 401
        return f(*args, **kwargs)
    return decorated_function

# Inicializar componentes
try:
    from app.services.waha_service import WahaService
    from app.agents.tools import db_manager
    waha = WahaService()
    agent_manager = get_agent()
    print("✅ Sistema Oclus inicializado com sucesso!")
except Exception as e:
    print(f"❌ Erro crítico na inicialização: {e}")
    sys.exit(1)

# --- ROTAS ADMIN DASHBOARD ---

@app.route('/admin')
def admin_dashboard():
    """Serve o dashboard administrativo."""
    return app.send_static_file('index.html')

@app.route('/api/admin/appointments', methods=['GET'])
@require_admin
def admin_list_appointments():
    """Lista consultas do dia para o dashboard."""
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    appts = db_manager.list_appointments(date_from=date)
    # Filtrar apenas para o dia específico se necessário (db_manager retorna >= date_from)
    day_appts = [a for a in appts if a['appointment_datetime'].startswith(date)]
    return jsonify({"success": True, "data": day_appts})

@app.route('/api/admin/soap_notes', methods=['GET'])
@require_admin
def admin_list_soap_notes():
    """Lista prontuários SOAP para assinatura."""
    limit = request.args.get('limit', 20, type=int)
    notes = db_manager.list_soap_notes(limit=limit)
    return jsonify({"success": True, "data": notes})

@app.route('/api/admin/soap_notes/<soap_id>/sign', methods=['POST'])
@require_admin
def admin_sign_soap_note(soap_id):
    """Assina um prontuário SOAP."""
    try:
        updated = db_manager.sign_soap_note(soap_id)
        return jsonify({"success": True, "data": updated})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/documents', methods=['POST'])
@require_admin
def admin_upload_document():
    """Endpoint para upload de documentos para o RAG com validação e logs de debug."""
    print(">>> [DEBUG] Recebendo requisição de upload...")
    if 'file' not in request.files:
        print(">>> [DEBUG] Erro: Campo 'file' ausente na requisição")
        return jsonify({"success": False, "error": "Nenhum arquivo enviado"}), 400

    file = request.files['file']
    if file.filename == '':
        print(">>> [DEBUG] Erro: Nome do arquivo está vazio")
        return jsonify({"success": False, "error": "Nome de arquivo vazio"}), 400

    print(f">>> [DEBUG] Recebido arquivo: {file.filename} (Mimetype: {file.mimetype})")

    # Validação de Extensão
    allowed_extensions = {'.pdf', '.txt'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        print(f">>> [DEBUG] Erro: Extensão {file_ext} não permitida")
        return jsonify({"success": False, "error": f"Extensão {file_ext} não permitida. Use PDF ou TXT."}), 400

    try:
        # Garantir diretório temporário
        TEMP_DIR.mkdir(exist_ok=True)
        
        filename = f"{uuid.uuid4()}_{file.filename}"
        filepath = TEMP_DIR / filename
        
        # Salvar arquivo
        file.save(filepath)
        
        # Validar tamanho (ex: 10MB)
        if filepath.stat().st_size > 10 * 1024 * 1024:
            filepath.unlink() # Deletar arquivo pesado
            return jsonify({"error": "Arquivo muito grande (máximo 10MB)"}), 400

        # Fase de Indexação
        from app.agents.rag import upload_clinic_document_tool
        # Ferramentas LangChain devem ser chamadas via .invoke()
        result = upload_clinic_document_tool.invoke({"file_path": str(filepath)})

        if "❌" in result:
            return jsonify({"success": False, "error": result}), 500

        return jsonify({"success": True, "message": result})

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        print(f">>> [CRÍTICO] Erro no processamento do upload:\n{error_details}")
        return jsonify({"success": False, "error": f"Erro interno: {str(e)}"}), 500

@app.route('/api/admin/documents_list', methods=['GET'])
@require_admin
def admin_list_documents():
    """Lista metadados dos documentos indexados."""
    try:
        docs = db_manager.list_documents()
        return jsonify({"success": True, "data": docs})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/admin/stats', methods=['GET'])
@require_admin
def admin_get_stats():
    """Retorna estatísticas de NPS para o dashboard."""
    days = request.args.get('days', 30, type=int)
    stats = db_manager.get_feedback_stats(days=days)
    return jsonify({"success": True, "data": stats})

# --- ROTAS WEBHOOK E PACIENTE ---
def download_media(url: str, extension: str) -> str:
    """Baixa o arquivo com validação básica (Prevenção SSRF)."""
    try:
        # Validação simples de domínio/url (poderia ser expandida)
        if not url.startswith(("http://", "https://")):
            return None
            
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        
        # Limite de tamanho (ex: 10MB)
        if len(response.content) > 10 * 1024 * 1024:
            return None
            
        filename = f"{uuid.uuid4()}.{extension}"
        filepath = TEMP_DIR / filename
        
        with open(filepath, "wb") as f:
            f.write(response.content)
            
        return str(filepath)
    except Exception as e:
        print(f"❌ Erro ao baixar mídia: {e}")
        return None

# Inicializar scheduler de confirmações (Evitar execução duplicada no Debug do Flask)
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    try:
        from app.core.scheduler import run_scheduler_background
        run_scheduler_background()
        print("✅ Scheduler de confirmações iniciado")
    except Exception as e:
        print(f"⚠️ Aviso: Falha ao iniciar scheduler: {e}")

# --- ROTAS ---

@app.route('/api/webhook', methods=['POST'])
def webhook():
    """Webhook para o WAHA (WhatsApp)."""
    try:
        data = request.json
        if not data:
            print("⚠️ Recebida requisição sem JSON")
            return jsonify({'status': 'error', 'message': 'No JSON data'}), 400

        event = data.get('event')
        print(f"DEBUG: Evento recebido: {event}")

        # Aceitar 'message' ou 'message.upsert' (comum em algumas versões/engines)
        if event not in ['message', 'message.upsert']:
            return jsonify({'status': 'ignored', 'reason': f'Event {event} not handled'}), 200

        payload = data.get('payload', {})
        
        # Log detalhado para debug
        chat_id = payload.get('from')
        from_me = payload.get('fromMe')
        body = payload.get('body')
        media = payload.get('media') # Suporte a mídias do WAHA
        
        print(f"DEBUG: Payload - From: {chat_id}, FromMe: {from_me}, Body: {body}")

        if from_me:
            print(f"ℹ️ Ignorando mensagem enviada pelo próprio bot ({chat_id})")
            return jsonify({'status': 'ignored', 'reason': 'fromMe is true'}), 200

        phone = chat_id.split('@')[0] if chat_id else "unknown"
        print(f"📩 Mensagem de {phone}: {body}")

        waha.start_typing(chat_id)
        
        # Processamento de Mídia ou Texto
        audio_path = None
        image_path = None
        
        if media and media.get('url'):
            mimetype = media.get('mimetype', '')
            ext = mimetype.split('/')[-1].split(';')[0] if '/' in mimetype else 'bin'
            filepath = download_media(media['url'], ext)
            
            if 'audio' in mimetype:
                audio_path = filepath
            elif 'image' in mimetype:
                image_path = filepath
            # Se for PDF ou outro, poderíamos adicionar lógica aqui
        
        response_text = agent_manager.process_message(
            body or "", 
            patient_phone=phone,
            audio_path=audio_path,
            image_path=image_path
        )

        print(f"🤖 Resposta para {phone}: {response_text}")

        waha.stop_typing(chat_id)
        waha.send_message(chat_id, response_text)
        
        return jsonify({'status': 'success'}), 200

    except Exception as e:
        print(f"❌ Erro no webhook: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/api/reset-memory', methods=['POST'])
def reset_memory():
    """Reseta a memória de um paciente específico."""
    data = request.json
    phone = data.get('phone')
    if not phone:
        return jsonify({"error": "Phone is required"}), 400
    
    agent_manager.reset_session(phone)
    return jsonify({"success": True, "message": f"Memória de {phone} resetada."})

@app.route('/api/health', methods=['GET'])
def health():
    """Endpoint de saúde com verificação de dependências."""
    results = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "database": {"status": "unknown"},
            "openai": {"status": "unknown"},
            "waha": {"status": "unknown"}
        }
    }
    
    # 1. Verificar Supabase
    try:
        from app.agents.tools import db_manager
        # Removida verificação de tabela 'clinics' para evitar erro 404
        db_manager.supabase.table("patients").select("id").limit(1).execute()
        results["services"]["database"]["status"] = "online"
    except Exception as e:
        results["services"]["database"] = {"status": "offline", "error": str(e)}
        results["status"] = "degraded"

    # 2. Verificar OpenAI
    try:
        import openai
        client = openai.Client()
        client.models.list() # Teste leve de conexão
        results["services"]["openai"]["status"] = "online"
    except Exception as e:
        results["services"]["openai"] = {"status": "offline", "error": str(e)}
        results["status"] = "degraded"

    # 3. Verificar WAHA
    try:
        waha_url = os.getenv("WHATSAPP_API_URL", "http://localhost:3000")
        response = requests.get(f"{waha_url}/api/health", timeout=5)
        if response.status_code == 200:
            results["services"]["waha"]["status"] = "online"
        else:
            results["services"]["waha"] = {"status": "offline", "code": response.status_code}
            results["status"] = "degraded"
    except Exception as e:
        results["services"]["waha"] = {"status": "offline", "error": str(e)}
        results["status"] = "degraded"

    return jsonify(results), 200 if results["status"] == "healthy" else 503

if __name__ == '__main__':
    host = os.getenv('API_HOST', '0.0.0.0')
    port = int(os.getenv('API_PORT', 3001))
    app.run(host=host, port=port, debug=True)
