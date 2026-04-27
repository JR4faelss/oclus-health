"""
Ferramentas para processamento multimodal: OCR e transcrição de áudio.
"""
import os
import io
import requests
import logging
import openai
from PIL import Image
import pytesseract

# Configuração de Logging
logger = logging.getLogger("OclusMultimodal")

# --- IMPORTAÇÕES RESILIENTES ---
def robust_import(paths, name):
    for path in paths:
        try:
            module = __import__(path, fromlist=[name])
            return getattr(module, name)
        except (ImportError, AttributeError, ModuleNotFoundError):
            continue
    return None

tool = robust_import(["langchain_core.tools", "langchain.tools"], "tool")
BaseModel = robust_import(["pydantic"], "BaseModel")
Field = robust_import(["pydantic"], "Field")
ChatOpenAI = robust_import(["langchain_openai", "langchain.chat_models"], "ChatOpenAI")

# Inicializar cliente OpenAI
openai_client = openai.Client()

# =================== ARGUMENTOS DAS TOOLS ====================

class ProcessImageArgs(BaseModel):
    file_path: str = Field(..., description="Caminho local ou URL da imagem")
    language: str = Field("por", description="Idioma para OCR")

class TranscribeAudioArgs(BaseModel):
    file_path: str = Field(..., description="Caminho local do arquivo de áudio")
    language: str = Field("pt", description="Código do idioma")

class ExtractPrescriptionArgs(BaseModel):
    image_path: str = Field(..., description="Caminho da imagem")

# =================== FERRAMENTAS ====================

@tool(args_schema=ProcessImageArgs)
def process_image_ocr_tool(file_path: str, language: str = "por") -> str:
    """Extrai texto de uma imagem usando OCR."""
    try:
        if file_path.startswith("http"):
            resp = requests.get(file_path, timeout=10)
            img = Image.open(io.BytesIO(resp.content))
        else:
            img = Image.open(file_path)
        text = pytesseract.image_to_string(img, lang=language)
        return text.strip() or "⚠️ Nenhum texto detectado."
    except Exception as e:
        return f"❌ Erro OCR: {str(e)}"

@tool(args_schema=TranscribeAudioArgs)
def transcribe_audio_tool(file_path: str, language: str = "pt") -> str:
    """Transcreve áudio usando OpenAI Whisper."""
    try:
        with open(file_path, "rb") as audio:
            transcript = openai_client.audio.transcriptions.create(model="whisper-1", file=audio, language=language)
        return transcript.text.strip()
    except Exception as e:
        return f"❌ Erro Transcrição: {str(e)}"

@tool(args_schema=ExtractPrescriptionArgs)
def extract_prescription_data_tool(image_path: str) -> str:
    """Extrai dados de uma prescrição médica."""
    try:
        ocr_res = process_image_ocr_tool(image_path)
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        res = llm.invoke(f"Extraia dados da prescrição: {ocr_res}")
        return f"📋 **Prescrição:**\n{res.content}"
    except Exception as e:
        return f"❌ Erro Prescrição: {str(e)}"

@tool
def process_multimodal_message_tool(file_path: str, media_type: str) -> str:
    """Detecta o tipo e chama a tool apropriada."""
    if media_type == "audio": return transcribe_audio_tool(file_path)
    if media_type == "image": return process_image_ocr_tool(file_path)
    if media_type == "prescription": return extract_prescription_data_tool(file_path)
    return "Mídia não suportada."
