import os
import logging
import base64
from openai import OpenAI
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("MediaParser")

# Cliente OpenAI para Whisper (Áudio)
client = OpenAI()

def transcribe_audio(file_path: str) -> str:
    """Transcreve áudio para texto usando OpenAI Whisper."""
    try:
        if not os.path.exists(file_path):
            return ""
        
        with open(file_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1", 
                file=audio_file
            )
        return transcript.text
    except Exception as e:
        logger.error(f"Erro na transcrição de áudio: {e}")
        return ""

def ocr_image_with_vision(file_path: str, prompt: str = "Extraia todo o texto desta imagem médica de forma legível.") -> str:
    """Extrai texto de imagem usando GPT-4o Vision."""
    try:
        if not os.path.exists(file_path):
            return ""

        # Codificar imagem em base64
        with open(file_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode('utf-8')

        llm = ChatOpenAI(model="gpt-4o") # Usando GPT-4o para melhor qualidade de visão
        
        message = HumanMessage(
            content=[
                {"type": "text", "text": prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"},
                },
            ]
        )
        
        response = llm.invoke([message])
        return response.content
    except Exception as e:
        logger.error(f"Erro no OCR Vision: {e}")
        return ""

def process_multimodal_input(audio_path: str = None, image_path: str = None) -> str:
    """Processa entradas multimídia e retorna uma string consolidada."""
    context = []
    
    if audio_path:
        text = transcribe_audio(audio_path)
        if text: context.append(f"[Transcrição de Áudio]: {text}")
        
    if image_path:
        text = ocr_image_with_vision(image_path)
        if text: context.append(f"[Texto extraído da Imagem/Exame]: {text}")
        
    return "\n".join(context)
