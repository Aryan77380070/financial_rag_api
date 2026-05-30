import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from sentence_transformers import CrossEncoder

# Use a fast, free local embedding model good for semantic search
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# Initialize ChromaDB locally in a 'chroma_db' directory
CHROMA_PATH = "chroma_db"

def get_vectorstore():
    return Chroma(persist_directory=CHROMA_PATH, embedding_function=embedding_model)

def process_and_index_document(document_id: int, file_path: str, metadata: dict):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found at {file_path}")

    # 1. Extract Text
    loader = PyPDFLoader(file_path)
    pages = loader.load()

    # 2. Chunking
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150, # Overlap prevents cutting off important sentences
        length_function=len
    )
    chunks = text_splitter.split_documents(pages)

    # Inject our relational DB metadata into the chunks
    for chunk in chunks:
        chunk.metadata.update(metadata)
        chunk.metadata["document_id"] = document_id 

    # 3. Embed and Store in Vector DB
    vectorstore = get_vectorstore()
    vectorstore.add_documents(chunks)
    
    return len(chunks)

def remove_document_embeddings(document_id: int):
    vectorstore = get_vectorstore()
    
    # Fetch all chunks belonging to this document_id
    collection = vectorstore.get()
    
    # Filter for the specific document's IDs
    ids_to_delete = []
    for i, metadata in enumerate(collection['metadatas']):
        if metadata.get('document_id') == document_id:
            ids_to_delete.append(collection['ids'][i])
            
    if ids_to_delete:
        vectorstore.delete(ids=ids_to_delete)
        
    return len(ids_to_delete)



# Initialize the reranker model (this will download on the first run)
# ms-marco is specifically trained for high-accuracy Question-Answering retrieval
reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def retrieve_and_rerank(query: str, top_k_initial: int = 20, top_k_final: int = 5):
    vectorstore = get_vectorstore()
    
    # 1. Vector Search (Initial fast retrieval of 20 results)
    initial_results = vectorstore.similarity_search(query, k=top_k_initial)
    
    if not initial_results:
        return []

    # 2. Reranking Preparation
    # Create pairs of [User Query, Document Chunk] for the Cross-Encoder to evaluate
    pairs = [[query, doc.page_content] for doc in initial_results]
    
    # 3. Predict Relevance Scores
    scores = reranker.predict(pairs)
    
    # 4. Sort and filter down to Top 5
    # Zip the documents with their new AI scores and sort them descending
    scored_results = list(zip(initial_results, scores))
    scored_results.sort(key=lambda x: x[1], reverse=True)
    
    top_results = scored_results[:top_k_final]
    
    # 5. Format the final output
    final_output = []
    for doc, score in top_results:
        final_output.append({
            "document_id": doc.metadata.get("document_id"),
            "title": doc.metadata.get("title", "Unknown"),
            "company_name": doc.metadata.get("company_name", "Unknown"),
            "content": doc.page_content,
            "relevance_score": float(score) # Convert numpy float to standard Python float
        })
        
    return final_output

def get_document_context(document_id: int):
    vectorstore = get_vectorstore()
    
    # Fetch all chunks belonging to this specific document_id
    collection = vectorstore.get()
    
    context_chunks = []
    for i, metadata in enumerate(collection['metadatas']):
        if metadata.get('document_id') == document_id:
            context_chunks.append(collection['documents'][i])
            
    return context_chunks

