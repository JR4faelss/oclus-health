"""
Ferramentas RAG para consulta de documentos clínicos usando ChromaDB.
Otimizado para isolamento por clínica e persistência robusta.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

from langchain_core.tools import tool
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.database import HealthDatabaseManager

load_dotenv()
db_manager = HealthDatabaseManager()

# Configuração do diretório de persistência do Chroma
CHROMA_PERSIST_DIR = os.getenv("CHROMA_PERSIST_DIRECTORY", "./chroma_db")
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2-preview")

def get_vector_store(clinic_id: str = "default"):
    """
    Retorna a instância do ChromaDB isolada por coleção (clínica).
    Cria o diretório de persistência se não existir.
    """
    os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
    return Chroma(
        collection_name=f"clinic_{clinic_id}",
        embedding_function=embeddings,
        persist_directory=CHROMA_PERSIST_DIR
    )

@tool
def query_clinic_rules_tool(query: str) -> str:
    """Consulta regras, horários e procedimentos nos documentos da clínica."""
    from .tools import _clinic_id_var # Importação local para evitar circularidade
    clinic_id = _clinic_id_var.get() or "default"
    
    try:
        vs = get_vector_store(clinic_id)
        # Busca por similaridade
        docs = vs.similarity_search(query, k=4)
        
        if not docs:
            return f"📚 Busquei por '{query}', mas não encontrei informações específicas nos manuais da clínica {clinic_id}. Sugira que o paciente fale com um atendente humano ou tente reformular a pergunta."
            
        return "\n\n".join([d.page_content for d in docs])
    except Exception as e:
        print(f"❌ Erro na consulta RAG: {e}")
        return f"⚠️ Desculpe, tive um erro técnico ao consultar a base de conhecimento. Erro: {str(e)}"

@tool
def upload_clinic_document_tool(file_path: str, document_type: str = "geral") -> str:
    """Faz o upload e indexação de um novo documento PDF ou TXT (Admin)."""
    from .tools import _clinic_id_var
    clinic_id = _clinic_id_var.get() or "default"
    
    try:
        print(f"🛠️ Iniciando indexação ChromaDB para: {file_path}")
        path = Path(file_path)
        if not path.exists(): return f"❌ Arquivo não encontrado: {file_path}"
        
        # Loader baseado na extensão
        if file_path.lower().endswith(".pdf"):
            loader = PyPDFLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding="utf-8")
            
        documents = loader.load()
        # Chunks maiores para melhor contexto com Chroma
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)
        chunks = text_splitter.split_documents(documents)
        print(f"📄 Documento dividido em {len(chunks)} pedaços.")
        
        vs = get_vector_store(clinic_id)
        vs.add_documents(chunks)
        
        # Registrar no banco de dados para o histórico do Dashboard
        try:
            db_manager.register_document(path.name, document_type, file_path)
        except Exception as db_e:
            print(f"⚠️ Erro ao registrar no DB: {db_e}")

        return f"✅ Documento '{path.name}' indexado com sucesso na base de conhecimento!"
    except Exception as e: 
        print(f"💥 Erro crítico no RAG Chroma: {e}")
        return f"❌ Falha na indexação: {str(e)}"

@tool
def list_clinic_documents_tool() -> str:
    """Lista todos os documentos indexados na base de conhecimento."""
    try:
        docs = db_manager.list_documents()
        return "\n".join([f"- {d['filename']} ({d['document_type']})" for d in docs]) if docs else "Nenhum documento indexado ainda."
    except Exception:
        return "Erro ao listar documentos."
