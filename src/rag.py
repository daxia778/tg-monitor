import os
import logging
from typing import List

try:
    import chromadb
except ImportError:
    chromadb = None

logger = logging.getLogger("tg-monitor.rag")

class RAGEngine:
    def __init__(self, db_path: str = "data/chroma", collection_name: str = "tg_messages"):
        self.db_path = db_path
        self._enabled = chromadb is not None
        
        if not self._enabled:
            logger.warning("⚠️ chromadb 未安装，RAG 功能已被禁用。请安装 chromadb。")
            return
            
        # Initialize chroma client
        os.makedirs(db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(path=db_path)
        
        # Determine embedding function
        ai_url = os.getenv("AI_API_URL", "")
        ai_key = os.getenv("AI_API_KEY", "")
        
        self.ef = None
        if ai_url and "/v1" in ai_url and os.getenv("USE_REMOTE_EMBEDDING", "false").lower() == "true":
            base_url = ai_url.split("/v1")[0] + "/v1"
            logger.info(f"🤖 RAG: 使用远程 OpenAI Embedding ({base_url})")
            from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction
            self.ef = OpenAIEmbeddingFunction(
                api_key=ai_key or "dummy",
                api_base=base_url,
                model_name=os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
            )
        else:
            logger.info("🤖 RAG: 使用本地默认 Embedding (all-MiniLM-L6-v2)")
            from chromadb.utils.embedding_functions import DefaultEmbeddingFunction
            self.ef = DefaultEmbeddingFunction()
            
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.ef
        )
        logger.info(f"✅ RAG: 向量数据库初始化完毕 ({collection_name})")
        
    def add_messages(self, messages: List[dict]):
        if not self._enabled or not messages:
            return
            
        ids = []
        documents = []
        metadatas = []
        
        for msg in messages:
            text = msg.get("text")
            if not text or len(text) < 5:
                continue
                
            msg_id = f"{msg['group_id']}_{msg['id']}"
            ids.append(msg_id)
            
            sender = msg.get("sender_name") or "Unknown"
            date = msg.get("date", "")
            
            # Limit text length to prevent breaking context limits on local embeddings
            if len(text) > 1500:
                text = text[:1500] + "..."
                
            doc = f"发送者: {sender}\n时间: {date}\n内容: {text}"
            documents.append(doc)
            
            metadatas.append({
                "group_id": msg["group_id"],
                "message_id": msg["id"],
                "sender_name": sender,
                "date": date
            })
            
        if not ids:
            return
            
        # Add to chroma in batches
        batch_size = 300
        for i in range(0, len(ids), batch_size):
            try:
                # Upsert updates existing items
                self.collection.upsert(
                    ids=ids[i:i+batch_size],
                    documents=documents[i:i+batch_size],
                    metadatas=metadatas[i:i+batch_size]
                )
            except Exception as e:
                logger.error(f"❌ RAG 添加消息向量失败: {e}")
                
    def search(self, query: str, n_results: int = 15) -> List[dict]:
        if not self._enabled:
            return []
            
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results
            )
            
            formatted_results = []
            if results and results['documents'] and len(results['documents']) > 0:
                docs = results['documents'][0]
                metas = results['metadatas'][0]
                
                for doc, meta in zip(docs, metas):
                    formatted_results.append({
                        "content": doc,
                        "metadata": meta
                    })
            return formatted_results
        except Exception as e:
            logger.error(f"❌ RAG 检索异常: {e}")
            return []
