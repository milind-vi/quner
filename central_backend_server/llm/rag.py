"""
Retrieval-Augmented Generation bootstrap.

Only initialises Pinecone + llama-index when ``config.USE_RAG`` is on. In
openai-only or groq-only mode this module exposes ``medical_knowledge_tool = None``
and the heavy dependencies are never imported.
"""

import config

medical_knowledge_tool = None

if config.USE_RAG:
    print("Initializing RAG (Pinecone + HuggingFace embeddings)...")
    from llama_index.core import VectorStoreIndex, StorageContext, Settings
    from llama_index.core import get_response_synthesizer
    from llama_index.core.query_engine import RetrieverQueryEngine
    from llama_index.core.retrievers import VectorIndexRetriever
    from llama_index.core.tools import QueryEngineTool
    from llama_index.core.vector_stores.types import VectorStoreQueryMode
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding
    from llama_index.llms.openai import OpenAI as RAGOpenAI
    from llama_index.vector_stores.pinecone import PineconeVectorStore
    from pinecone import Pinecone

    Settings.llm = RAGOpenAI(model=config.VSP_model_ragprocessing, temperature=0.1)
    pc = Pinecone(api_key=config.PINECONE_API_KEY)
    pinecone_index = pc.Index(config.pinecone_index_name)

    embed_model = HuggingFaceEmbedding(
        model_name=config.RAG_EMBEDDING_MODEL,
        device="cpu",
    )
    vector_store = PineconeVectorStore(pinecone_index=pinecone_index)
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    index = VectorStoreIndex.from_vector_store(
        vector_store, storage_context=storage_context, embed_model=embed_model
    )
    medical_knowledge_tool = QueryEngineTool.from_defaults(
        query_engine=RetrieverQueryEngine(
            retriever=VectorIndexRetriever(
                index=index,
                similarity_top_k=3,
                vector_store_query_mode=VectorStoreQueryMode.DEFAULT,
            ),
            response_synthesizer=get_response_synthesizer(),
        ),
        name="medical_knowledge",
        description="A RAG engine that is the only source of medical knowledge for a general practitioner.",
    )
else:
    print(
        f"RAG disabled (PIPELINE_MODE={config.PIPELINE_MODE}, USE_RAG={config.USE_RAG}). "
        "Patient responses will not be grounded in EBM corpus."
    )
