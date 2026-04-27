import os
import sys
from unittest.mock import MagicMock, patch

# Adiciona o diretório raiz ao path para encontrar o módulo app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.agents.agent import get_agent

def test_system():
    # Inicializa o agente
    agent = get_agent()
    patient_phone = "5511999999999"
    
    print("\n" + "="*50)
    print("🚀 INICIANDO TESTES DO SISTEMA MULTIAGENTE OCLUS")
    print("="*50 + "\n")

    # TESTE 1: Recepcionista (RAG / Informações)
    print("--- Teste 1: Recepcionista (Fluxo de Agendamento/Info) ---")
    resp1 = agent.process_message("Quais são as regras de cancelamento da clínica?", patient_phone)
    print(f"Paciente: Regras de cancelamento?\nIA: {resp1}\n")

    # TESTE 2: Triagem (Sintomas e Especialidade)
    print("--- Teste 2: Triagem (Avaliação de Sintomas) ---")
    resp2 = agent.process_message("Estou sentindo uma dor no peito que irradia para o braço esquerdo.", patient_phone)
    print(f"Paciente: Dor no peito...\nIA: {resp2}\n")

    # TESTE 3: Multimodal (Simulação de Áudio)
    print("--- Teste 3: Áudio (Transcrição via Whisper) ---")
    with patch('app.utils.media_parser.transcribe_audio') as mock_audio:
        mock_audio.return_value = "Eu gostaria de marcar um retorno com o Dr. Ricardo na próxima quinta às dez da manhã."
        resp3 = agent.process_message("", patient_phone, audio_path="mock_audio.mp3")
        print(f"Paciente: [Áudio Transcrito]\nIA: {resp3}\n")

    # TESTE 4: Multimodal (Simulação de Imagem/OCR)
    print("--- Teste 4: Imagem (OCR de Exame via GPT-4o Vision) ---")
    with patch('app.utils.media_parser.ocr_image_with_vision') as mock_ocr:
        mock_ocr.return_value = "RELATÓRIO MÉDICO: Paciente apresenta inflamação leve na garganta. Recomendado repouso e hidratação. Assinado: Dra. Ana."
        resp4 = agent.process_message("Pode ler o que diz esse papel que o médico me deu?", patient_phone, image_path="mock_receita.jpg")
        print(f"Paciente: [Enviou Foto de Receita]\nIA: {resp4}\n")

    # TESTE 5: Clínico (Prontuário/Admin)
    print("--- Teste 5: Clínico (Uso Administrativo/Médico) ---")
    resp5 = agent.process_message("Busque meu último histórico de atendimento, por favor.", patient_phone)
    print(f"Paciente: Buscar histórico.\nIA: {resp5}\n")

    print("="*50)
    print("✅ TESTES CONCLUÍDOS COM SUCESSO!")
    print("="*50 + "\n")

if __name__ == "__main__":
    try:
        test_system()
    except Exception as e:
        print(f"❌ Falha durante a execução dos testes: {e}")
