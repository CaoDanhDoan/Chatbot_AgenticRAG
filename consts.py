import os
import chromadb
import google.generativeai as genai
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))

model = SentenceTransformer("BAAI/bge-m3")
reranker_model = CrossEncoder("BAAI/bge-reranker-base")

gemini_fast_llm = ChatGoogleGenerativeAI(
    model=os.environ.get("GEN_FAST_MODEL", "gemini-2.5-flash-lite"),
    temperature=float(os.environ.get("GEN_TEMPERATURE", "0.2")),
    max_output_tokens=int(os.environ.get("GEN_MAX_OUTPUT_TOKENS", "2048")),
)
gemini_strong_llm = ChatGoogleGenerativeAI(
    model=os.environ.get("GEN_STRONG_MODEL", "gemini-2.5-flash"),
    temperature=float(os.environ.get("GEN_TEMPERATURE", "0.2")),
    max_output_tokens=int(os.environ.get("GEN_MAX_OUTPUT_TOKENS_STRONG", "512")),
)

client = chromadb.CloudClient(
    api_key=os.environ.get("CHROMA_API_KEY"),
    tenant=os.environ.get("CHROMA_TENANT"),
    database=os.environ.get("CHROMA_DATABASE"),
)

collection = client.get_collection(os.environ.get("CHROMA_COLLECTION_NAME"))
