import os
import chromadb
import google.generativeai as genai
from sentence_transformers import SentenceTransformer, CrossEncoder
from langchain_google_genai import ChatGoogleGenerativeAI
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()

model = SentenceTransformer('BAAI/bge-m3')
reranker_model = CrossEncoder('BAAI/bge-reranker-base')
gemini_fast_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0.2)
gemini_strong_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-lite", temperature=0.2)
client = chromadb.CloudClient(
    api_key=os.environ.get("CHROMA_API_KEY"),
    tenant=os.environ.get("CHROMA_TENANT"),
    database=os.environ.get("CHROMA_DATABASE")
)
collection = client.get_collection(os.environ.get("CHROMA_COLLECTION_NAME"))
