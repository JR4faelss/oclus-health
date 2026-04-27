import os
from dotenv import load_dotenv
from langchain_google_genai import GoogleGenerativeAIEmbeddings

load_dotenv()

def test_gemini_embeddings():
    if not os.getenv("GOOGLE_API_KEY"):
        print("❌ GOOGLE_API_KEY não encontrada no .env")
        return

    try:
        print("🔍 Testando Gemini Embedding 2 (models/gemini-embedding-2-preview)...")
        embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-2-preview")
        
        text = "Oclus Health é o melhor assistente de saúde."
        vector = embeddings.embed_query(text)
        
        print(f"✅ Sucesso! Vetor gerado com tamanho: {len(vector)}")
        print(f"Primeiros 5 valores: {vector[:5]}")
    except Exception as e:
        print(f"❌ Erro ao testar embeddings: {e}")

if __name__ == "__main__":
    test_gemini_embeddings()
