"""
Long-term memory management using Chroma vector database.
Provides persistent storage for project documents, decisions, and knowledge.
"""

from typing import Any, Optional

from multi_agent.core.types import AgentRole


class LongTermMemoryManager:
    """
    Manages long-term memory using Chroma vector database.
    
    Stores:
    - Project documents and specifications
    - Decision records and rationale
    - Bug history and resolutions
    - Knowledge base for advisor analysis
    
    Provides semantic search capabilities for retrieving relevant information.
    """
    
    def __init__(
        self,
        persist_directory: Optional[str] = None,
        embedding_model: str = "all-MiniLM-L6-v2",
    ):
        self.persist_directory = persist_directory
        self.embedding_model = embedding_model
        self._client = None
        self._collections: dict[str, Any] = {}
        
        self._default_collections = [
            "project_documents",
            "decisions",
            "bug_history",
            "knowledge_base",
            "agent_interactions",
        ]
    
    def _get_client(self) -> Any:
        """Lazy initialization of Chroma client."""
        if self._client is None:
            try:
                import chromadb
                from chromadb.config import Settings
                
                if self.persist_directory:
                    settings = Settings(
                        persist_directory=self.persist_directory,
                        anonymized_telemetry=False,
                    )
                    self._client = chromadb.Client(settings)
                else:
                    self._client = chromadb.Client()
                    
            except ImportError:
                raise RuntimeError(
                    "chromadb is required for long-term memory. "
                    "Install it with: pip install chromadb"
                )
        
        return self._client
    
    def _get_or_create_collection(self, name: str) -> Any:
        """Get or create a collection by name."""
        if name not in self._collections:
            client = self._get_client()
            self._collections[name] = client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collections[name]
    
    async def store(
        self,
        content: str,
        metadata: dict[str, Any],
        collection: str = "project_documents",
        doc_id: Optional[str] = None,
    ) -> str:
        """
        Store content in the vector database.
        
        Returns the document ID for future reference.
        """
        import uuid
        
        collection_obj = self._get_or_create_collection(collection)
        
        doc_id = doc_id or str(uuid.uuid4())
        
        collection_obj.add(
            documents=[content],
            metadatas=[metadata],
            ids=[doc_id],
        )
        
        return doc_id
    
    async def store_batch(
        self,
        contents: list[str],
        metadatas: list[dict[str, Any]],
        collection: str = "project_documents",
        doc_ids: Optional[list[str]] = None,
    ) -> list[str]:
        """
        Store multiple documents at once.
        
        Returns list of document IDs.
        """
        import uuid
        
        collection_obj = self._get_or_create_collection(collection)
        
        if doc_ids is None:
            doc_ids = [str(uuid.uuid4()) for _ in contents]
        
        collection_obj.add(
            documents=contents,
            metadatas=metadatas,
            ids=doc_ids,
        )
        
        return doc_ids
    
    async def retrieve(
        self,
        query: str,
        collection: str = "project_documents",
        n_results: int = 5,
        where_filter: Optional[dict] = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant documents using semantic search.
        
        Returns list of documents with their content, metadata, and distance.
        """
        collection_obj = self._get_or_create_collection(collection)
        
        query_params = {
            "query_texts": [query],
            "n_results": n_results,
        }
        
        if where_filter:
            query_params["where"] = where_filter
        
        results = collection_obj.query(**query_params)
        
        documents = []
        if results["documents"] and results["documents"][0]:
            for i, doc in enumerate(results["documents"][0]):
                document = {
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "id": results["ids"][0][i] if results["ids"] else None,
                    "distance": results["distances"][0][i] if results.get("distances") else None,
                }
                documents.append(document)
        
        return documents
    
    async def delete(
        self,
        doc_ids: list[str],
        collection: str = "project_documents",
    ) -> None:
        """Delete documents by their IDs."""
        collection_obj = self._get_or_create_collection(collection)
        collection_obj.delete(ids=doc_ids)
    
    async def update(
        self,
        doc_id: str,
        content: str,
        metadata: dict[str, Any],
        collection: str = "project_documents",
    ) -> None:
        """Update an existing document."""
        collection_obj = self._get_or_create_collection(collection)
        collection_obj.update(
            ids=[doc_id],
            documents=[content],
            metadatas=[metadata],
        )
    
    def get_collection_stats(self, collection: str) -> dict[str, Any]:
        """Get statistics about a collection."""
        collection_obj = self._get_or_create_collection(collection)
        count = collection_obj.count()
        
        return {
            "name": collection,
            "count": count,
        }
    
    def list_collections(self) -> list[str]:
        """List all available collections."""
        client = self._get_client()
        collections = client.list_collections()
        return [c.name for c in collections]
    
    async def store_decision(
        self,
        decision: str,
        context: dict[str, Any],
        made_by: AgentRole,
        task_id: Optional[str] = None,
    ) -> str:
        """
        Store a decision record with context.
        
        Useful for advisor analysis of past decisions.
        """
        metadata = {
            "type": "decision",
            "made_by": made_by.value,
            "task_id": task_id,
            **context,
        }
        
        return await self.store(
            content=decision,
            metadata=metadata,
            collection="decisions",
        )
    
    async def store_bug_resolution(
        self,
        bug_description: str,
        resolution: str,
        context: dict[str, Any],
    ) -> str:
        """
        Store a bug and its resolution for future reference.
        """
        content = f"Bug: {bug_description}\n\nResolution: {resolution}"
        metadata = {
            "type": "bug_resolution",
            **context,
        }
        
        return await self.store(
            content=content,
            metadata=metadata,
            collection="bug_history",
        )
    
    async def find_similar_issues(
        self,
        query: str,
        n_results: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Find similar past issues or bugs.
        
        Used by advisor committee for analysis.
        """
        results = await self.retrieve(
            query=query,
            collection="bug_history",
            n_results=n_results,
        )
        
        decisions = await self.retrieve(
            query=query,
            collection="decisions",
            n_results=n_results,
        )
        
        return results + decisions
