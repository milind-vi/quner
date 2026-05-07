"""
Build / populate Pinecone with EBM documents for RAG.

Embedding is CPU-friendly (config.RAG_EMBEDDING_MODEL, 384-d). Your Pinecone index
must be created with dimension RAG_EMBEDDING_DIMENSION. If you had an old Stella
(1024-d) index, create a new index (new name or delete old) then run this script.

1. In Pinecone console (or uncomment create_index below once), create index with dimension 384.
2. Set ebm_source_path to your folder of .md (etc.) files.
3. python create_rag_storage.py
"""
import os
import sys

# Allow importing central_backend_server config when run from repo root
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, os.path.join(_REPO_ROOT, "central_backend_server"))
import config as _central_config

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pinecone import Pinecone, ServerlessSpec
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.vector_stores.pinecone import PineconeVectorStore

# Variables (override or set in central_backend_server/config.py for embedding model/dimension)
api_key = ""  # The Pinecone API key — or set PINECONE_API_KEY in central_backend_server/config.py
pinecone_index_name = ""  # Must match central_backend_server config pinecone_index_name
ebm_source_path = ""  # Path to EBM sources, no trailing slash

# Embedding must match central_backend_server/utils.py (config.RAG_EMBEDDING_MODEL / DIMENSION).
# CPU-friendly default: all-MiniLM-L6-v2 @ 384-d — no xFormers, no GPU required.
if api_key:
    _pc = Pinecone(api_key=api_key)
else:
    _pc = Pinecone(api_key=_central_config.PINECONE_API_KEY)

# Create index only if it does not exist (avoid error on re-run); dimension must match embedding model
# pinecone_index_name and dimension must align with config
_RAG_DIM = _central_config.RAG_EMBEDDING_DIMENSION
_RAG_MODEL = _central_config.RAG_EMBEDDING_MODEL

# Uncomment to create a new index (fails if name already exists with different dimension)
# _pc.create_index(
#     name=pinecone_index_name or _central_config.pinecone_index_name,
#     dimension=_RAG_DIM,
#     metric="euclidean",
#     spec=ServerlessSpec(cloud="aws", region="us-east-1"),
# )

pinecone_index_name = pinecone_index_name or _central_config.pinecone_index_name
if not pinecone_index_name:
    raise SystemExit("Set pinecone_index_name (here or in central_backend_server/config.py).")
if not ebm_source_path or not os.path.isdir(ebm_source_path):
    raise SystemExit("Set ebm_source_path to a folder of EBM documents (e.g. .md files).")

pinecone_index = _pc.Index(pinecone_index_name)

embed_model = HuggingFaceEmbedding(
    model_name=_RAG_MODEL,
    device="cpu",
)
documents = SimpleDirectoryReader(ebm_source_path).load_data()
vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
storage_context = StorageContext.from_defaults(vector_store=vector_store)
index = VectorStoreIndex.from_documents(
    documents, storage_context=storage_context, show_progress = True, embed_model=embed_model
)