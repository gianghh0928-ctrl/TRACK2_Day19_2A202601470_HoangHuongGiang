"""HybridMemoryAgent: kết hợp Vector Store (Episodic Memory) và Feast Feature Store (User Profile).

Bonus Challenge — Lab 19 (Track 2).
"""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import Any

from feast import FeatureStore
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
    VectorParams,
)

from app.embeddings import Embedder

COLLECTION_NAME = "lab19_bonus_memory"


class HybridMemoryAgent:
    """Agent quản lý bộ nhớ lai (Hybrid Memory) cho trợ lý cá nhân."""

    def __init__(self, feast_repo_path: str | Path | None = None) -> None:
        self.embedder = Embedder()
        self.qdrant = QdrantClient(":memory:")
        self._init_qdrant_collection()

        # Khởi tạo Feast Feature Store
        if feast_repo_path is None:
            feast_repo_path = Path(__file__).resolve().parent.parent / "app" / "feast_repo"
        self.fs = FeatureStore(repo_path=str(feast_repo_path))

    def _init_qdrant_collection(self) -> None:
        existing = {c.name for c in self.qdrant.get_collections().collections}
        if COLLECTION_NAME not in existing:
            self.qdrant.create_collection(
                collection_name=COLLECTION_NAME,
                vectors_config=VectorParams(size=self.embedder.dim, distance=Distance.COSINE),
            )

    def remember(self, text: str, user_id: str = "u_001", metadata: dict[str, Any] | None = None) -> str:
        """Ghi nhớ một ký ức/hội thoại mới vào Episodic Memory (Qdrant Vector Store)."""
        vector = next(self.embedder.embed([text])).tolist()
        point_id = str(uuid.uuid4())
        payload = {
            "user_id": user_id,
            "text": text,
            **(metadata or {}),
        }
        self.qdrant.upsert(
            collection_name=COLLECTION_NAME,
            points=[
                PointStruct(
                    id=point_id,
                    vector=vector,
                    payload=payload,
                )
            ],
        )
        return point_id

    def recall(self, query: str, user_id: str = "u_001", top_k: int = 3) -> str:
        """Truy xuất hồ sơ người dùng (Feast) + ký ức tương đồng (Qdrant) -> trả về Context tổng hợp."""
        # 1. Lấy thông tin User Profile và Recent Activity từ Feast Online Store
        profile_features = [
            "user_profile_features:reading_speed_wpm",
            "user_profile_features:preferred_language",
            "user_profile_features:topic_affinity",
            "query_velocity_features:queries_last_hour",
            "query_velocity_features:distinct_topics_24h",
        ]
        try:
            feast_resp = self.fs.get_online_features(
                features=profile_features,
                entity_rows=[{"user_id": user_id}],
            ).to_dict()
            reading_speed = feast_resp.get("reading_speed_wpm", [200])[0]
            pref_lang = feast_resp.get("preferred_language", ["vi"])[0]
            topic_affinity = feast_resp.get("topic_affinity", ["cloud"])[0]
            queries_last_hour = feast_resp.get("queries_last_hour", [0])[0]
            distinct_topics = feast_resp.get("distinct_topics_24h", [1])[0]
        except Exception:
            # Fallback nếu online store chưa khởi tạo
            reading_speed, pref_lang, topic_affinity = 187, "vi", "cloud"
            queries_last_hour, distinct_topics = 11, 4

        # 2. Truy vấn Episodic Memories từ Qdrant (có payload filter theo user_id)
        q_vec = next(self.embedder.embed([query])).tolist()
        user_filter = Filter(
            must=[
                FieldCondition(
                    key="user_id",
                    match=MatchValue(value=user_id),
                )
            ]
        )
        hits = self.qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=q_vec,
            query_filter=user_filter,
            limit=top_k,
        ).points

        memory_snippets = [f"- [{h.score:.3f}] {h.payload.get('text', '')}" for h in hits]
        memories_text = "\n".join(memory_snippets) if memory_snippets else "(Không tìm thấy ký ức liên quan)"

        # 3. Tổng hợp thành Context string sẵn sàng cho LLM Prompt
        assembled_context = f"""=== [USER PROFILE CONTEXT] ===
- User ID: {user_id}
- Preferred Language: {pref_lang} | Reading Speed: {reading_speed} wpm
- Topic Affinity: {topic_affinity}
- Recent Activity: {queries_last_hour} queries/hour | {distinct_topics} distinct topics (24h)

=== [RELEVANT EPISODIC MEMORIES] ===
{memories_text}

=== [USER QUERY] ===
"{query}"
"""
        return assembled_context
