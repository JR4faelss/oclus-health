# 🏥 Oclus Health Assistant - Guia de Uso

## 📋 Passo a Passo para Implantação

### 1️⃣ Preparar o Ambiente

```bash
# Clonar/baixar o projeto
cd oclus_health

# Criar ambiente virtual
python -m venv venv

# Ativar (Windows)
venv\Scripts\activate

# Ativar (Linux/Mac)
source venv/bin/activate

# Instalar dependências
pip install -r requirements.txt
```

### 2️⃣ Configurar Supabase

1. Acesse [supabase.com](https://supabase.com) e crie um projeto
2. Vá em **SQL Editor** e execute o arquivo `schema.sql`
3. Copie as credenciais:
   - SUPABASE_URL
   - SUPABASE_SERVICE_ROLE_KEY

### 3️⃣ Configurar Variáveis de Ambiente

```bash
# Copiar template
cp .env.example .env

# Editar .env com suas credenciais
# - OpenAI API Key
# - Supabase URL e Keys
# - WhatsApp API URL
```

### 4️⃣ Carregar Documentos da Clínica (RAG)

Crie uma pasta `documents/` e adicione seus PDFs/TXTs:

```bash
mkdir documents
# Adicionar: manual_clinica.pdf, precos.pdf, convenios.txt, etc.
```

Execute o script para indexar:

```bash
# Exemplo de comando via python -m
python -c "from app.agents.rag import upload_clinic_document_tool; upload_clinic_document_tool('./documents/manual_clinica.pdf')"
```

### 5️⃣ Rodar a API

```bash
python -m app.api.routes
```

A API estará disponível em `http://localhost:3001`

### 6️⃣ Rodar o Scheduler (em outro terminal - opcional se rodar via API)

```bash
python -m app.core.scheduler
```

---

## 🧪 Testar o Sistema

### Teste 1: Cadastro de Paciente

**Paciente:** "Olá, quero agendar uma consulta"

**Oclus:** "Olá! Para agendar, preciso de alguns dados. Qual seu nome completo?"

**Paciente:** "João Silva"

**Oclus:** "Obrigado, João! Qual seu telefone?"

**Paciente:** "83996210460"

✅ Paciente cadastrado automaticamente.

### Teste 2: Agendar Consulta

**Paciente:** "Quero agendar com Dr. Carlos amanhã às 14h"

**Oclus:** (verifica disponibilidade)
"✅ Consulta agendada!
📅 Data: 2025-12-13
🕐 Horário: 14:00
👨‍⚕️ Dr. Carlos"

### Teste 3: Consultar Informações (RAG)

**Paciente:** "Quanto custa uma limpeza?"

**Oclus:** (busca no documento carregado)
"📚 Segundo nosso manual de procedimentos:
Limpeza básica: R$ 150,00
Limpeza completa: R$ 250,00"

### Teste 4: Listar Consultas

**Paciente:** "Quais são minhas consultas?"

**Oclus:** "📋 Suas consultas:
✅ #1 - 13/12/2025 às 14:00
   👨‍⚕️ Dr. Carlos"

---

## 🔗 Integração com WhatsApp

### Opção 1: Evolution API (Recomendado)

```bash
# Instalar Evolution API
docker pull atendai/evolution-api

docker run -d \
  --name evolution-api \
  -p 8080:8080 \
  atendai/evolution-api
```

Configure no `.env`:
```env
WHATSAPP_API_URL=http://localhost:8080
WHATSAPP_INSTANCE_NAME=oclus_health
```

### Opção 2: Outras APIs

- **Twilio**: Adaptar `send_whatsapp_message()` em `confirmation_scheduler.py`
- **WPPConnect**: Ajustar endpoints
- **Baileys**: Configurar servidor próprio

---

## 📊 Funcionalidades Adicionais Sugeridas

### 1. **Integração com Google Calendar**
```python
# Similar ao código original (google_calendar_service.py)
# Sincronizar consultas agendadas com calendário do médico
```

### 2. **Lembretes via SMS** (além de WhatsApp)
```python
# Usar Twilio SMS API
from twilio.rest import Client

def send_sms_reminder(phone, message):
    client = Client(account_sid, auth_token)
    client.messages.create(to=phone, from_=twilio_phone, body=message)
```

### 3. **Dashboard Administrativo**
```python
# Flask + Dash para visualizar:
# - Consultas do dia
# - Taxa de confirmação
# - NPS Score
# - Horários mais procurados
```

### 4. **Exportar Prontuários para PDF**
```python
from reportlab.pdfgen import canvas

def export_soap_to_pdf(soap_note):
    # Gerar PDF formatado do prontuário SOAP
    pass
```

### 5. **Análise de Sentimento em Feedbacks**
```python
# Já implementado em feedback_tools.py
# analyze_feedback_sentiment_tool
```

### 6. **Notificações Push (para médicos)**
```python
# Firebase Cloud Messaging
# Notificar médico quando paciente chega
```

### 7. **Fila de Espera**
```python
# Quando não houver vaga, adicionar à lista de espera
# Notificar quando surgir cancelamento
```

### 8. **Prescrições Digitais**
```python
# Gerar e enviar prescrições via WhatsApp
# Com assinatura digital do médico
```

---

## 🎯 Próximos Passos

1. ✅ **Testar localmente** com documentos reais da clínica
2. ✅ **Conectar WhatsApp** e fazer testes com pacientes piloto
3. ✅ **Ajustar prompts** baseado em feedback real
4. ✅ **Adicionar mais documentos** ao RAG
5. ✅ **Deploy em produção** (Railway, Render, AWS, etc.)
6. ✅ **Monitorar métricas** (taxa de confirmação, satisfação)

---

## 💡 Dicas de Vendas

### Benefícios para Clínicas:

✅ **Redução de No-Shows** - Lembretes automáticos aumentam comparecimento
✅ **Atendimento 24/7** - Pacientes podem agendar a qualquer hora
✅ **Organização** - Prontuários digitais padronizados (SOAP)
✅ **Satisfação** - Coleta automática de feedback
✅ **Eficiência** - Recepcionista foca em tarefas mais importantes

### Modelo de Precificação:

- **Plano Básico**: R$ 297/mês
  - Até 500 mensagens
  - Agendamento + Confirmações
  - Suporte por e-mail

- **Plano Profissional**: R$ 597/mês
  - Mensagens ilimitadas
  - Prontuários SOAP
  - RAG com documentos
  - Suporte prioritário

- **Plano Enterprise**: R$ 997/mês
  - Multi-clínica
  - Dashboard personalizado
  - Integrações customizadas
  - Consultoria incluída

---

## 🆘 Suporte

Em caso de dúvidas ou problemas:
1. Verificar logs: `api_agent.py` e `confirmation_scheduler.py`
2. Testar conexões: Supabase, OpenAI, WhatsApp API
3. Revisar `.env` e variáveis de ambiente
4. Consultar documentação das APIs utilizadas

---

**Desenvolvido usando LangChain + WhatsApp + Supabase**
