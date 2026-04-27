# 🏥 Oclus Health Assistant

Assistente de IA Multiagente para Clínicas de Saúde usando LangChain + WhatsApp API

## 🎯 Público-Alvo
- 🦷 Dentistas
- 👨‍⚕️ Médicos
- 🧘 Fisioterapeutas  
- 🥗 Nutricionistas

## 🚀 Funcionalidades

### Core Features
- ✅ **Agendamento Inteligente** - Agenda consultas com verificação de disponibilidade
- 📞 **Confirmação de Presença** - Sistema automático de lembretes e confirmação
- 📋 **Prontuários SOAP** - Resumo estruturado (Subjetivo, Objetivo, Avaliação, Plano)
- 📚 **RAG para Regras da Clínica** - Leitura de PDFs/TXTs com contexto sobre procedimentos
- ⭐ **Feedback Pós-Consulta** - Coleta automática de satisfação
- 💬 **Atendimento 24/7** - Responde dúvidas sobre horários, procedimentos, convênios

### Tools Disponíveis
1. **Agendamento**
   - `create_appointment_tool` - Criar nova consulta
   - `list_appointments_tool` - Listar consultas
   - `cancel_appointment_tool` - Cancelar/remarcar
   - `check_availability_tool` - Verificar horários disponíveis

2. **Confirmação**
   - `send_confirmation_tool` - Enviar lembrete de confirmação
   - `mark_confirmed_tool` - Registrar confirmação do paciente
   - `list_pending_confirmations_tool` - Listar não confirmados

3. **Prontuários SOAP**
   - `create_soap_note_tool` - Criar nota SOAP
   - `get_patient_history_tool` - Histórico completo
   - `update_soap_note_tool` - Atualizar prontuário

4. **RAG (Documentos)**
   - `query_clinic_rules_tool` - Buscar informações em documentos
   - `upload_clinic_document_tool` - Adicionar novo PDF/TXT
   - `list_documents_tool` - Listar documentos indexados

5. **Feedback**
   - `send_feedback_request_tool` - Solicitar avaliação
   - `collect_feedback_tool` - Registrar feedback
   - `get_feedback_stats_tool` - Estatísticas de satisfação

6. **Pacientes**
   - `register_patient_tool` - Cadastrar novo paciente
   - `get_patient_info_tool` - Buscar dados do paciente
   - `update_patient_tool` - Atualizar informações

## 📦 Estrutura do Projeto

```
oclus_health/
├── app/
│   ├── api/                # API Flask e Rotas
│   │   └── routes.py       
│   ├── agents/             # Lógica do Agente e Ferramentas
│   │   ├── agent.py        # Coração do assistente (LangGraph)
│   │   ├── tools.py        # Ferramentas de negócio (Agendamento, SOAP, etc)
│   │   ├── rag.py          # Ferramentas de busca em documentos (RAG)
│   │   └── messages.py     # Processamento de mensagens multimodais
│   ├── core/               # Núcleo do Sistema
│   │   ├── database.py     # Gerenciador Supabase
│   │   └── scheduler.py    # Sistema de confirmações automáticas
│   ├── services/           # Serviços Externos
│   │   └── waha_service.py # Integração WhatsApp (WAHA)
│   └── utils/              # Utilitários e Diagnósticos
│       └── diagnose.py
├── tests/                  # Testes Automatizados
│   └── test_agent.py
├── .env                    # Variáveis de Ambiente
├── docker-compose.yml      # Infraestrutura (WAHA + Redis)
├── requirements.txt        # Dependências do projeto
└── README.md               # Documentação
```

## 🔧 Instalação e Execução

```bash
# 1. Criar ambiente virtual
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Instalar dependências
pip install -r requirements.txt

# 3. Executar a API
python -m app.api.routes

# 4. Executar o Scheduler de Confirmações (opcional se não rodar via API)
python -m app.core.scheduler
```
# 4. Rodar API
python api_agent.py
```

## 🌐 Variáveis de Ambiente (.env)

```env
# OpenAI
OPENAI_API_KEY=sk-...

# Supabase
SUPABASE_URL=https://...
SUPABASE_SERVICE_ROLE_KEY=...

# WhatsApp (Evolution API ou similar)
WHATSAPP_API_URL=http://localhost:8080
WHATSAPP_INSTANCE_NAME=oclus

# Embedding (para RAG)
EMBEDDING_MODEL=text-embedding-3-small

# ChromaDB (RAG)
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

## 📝 Exemplo de Uso

### Paciente agenda consulta:
```
Paciente: "Oi, quero agendar uma consulta"
Oclus: "Olá! Vou te ajudar a agendar. Para qual dia você gostaria?"
Paciente: "Amanhã às 14h"
Oclus: "✅ Consulta agendada para 13/12/2025 às 14:00. 
        Você receberá um lembrete 24h antes para confirmação."
```

### Paciente pergunta sobre procedimento:
```
Paciente: "Quanto custa uma limpeza?"
Oclus: [busca no RAG dos documentos da clínica]
       "Segundo nosso manual de procedimentos, a limpeza básica custa R$ 150,00..."
```

## 🤖 Técnicas de IA Utilizadas

- **LangChain Agents** - Orquestração de ferramentas
- **RAG (Retrieval-Augmented Generation)** - ChromaDB + OpenAI Embeddings
- **Function Calling** - OpenAI GPT-4 com ferramentas estruturadas
- **Prompt Engineering** - Sistema especializado em saúde
- **Memory** - ConversationBufferMemory para contexto

## 📊 Métricas e Analytics

O sistema coleta automaticamente:
- Taxa de confirmação de consultas
- NPS (Net Promoter Score) dos feedbacks
- Horários com maior demanda
- Tipos de dúvidas mais frequentes
- Taxa de não comparecimento

## 🔐 Segurança e LGPD

- ✅ Dados de saúde criptografados
- ✅ Conformidade com LGPD
- ✅ Logs auditáveis
- ✅ Consentimento do paciente registrado

## 📞 Suporte

Para dúvidas ou sugestões, entre em contato!
