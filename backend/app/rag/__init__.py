# RAG (Retrieval-Augmented Generation) package — built with LangChain
#
# Files in this folder:
#   embeddings.py   — HuggingFaceEmbeddings: converts text → 384-dim vectors (local, free)
#   llm.py          — ChatGroq: Llama 3 8B via Groq API (free tier)
#   vectorstore.py  — PGVector: stores/searches document chunks in PostgreSQL
#   chain.py        — LCEL RAG chain: wires retriever | prompt | llm together
