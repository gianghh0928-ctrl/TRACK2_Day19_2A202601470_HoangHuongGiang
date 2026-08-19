"""Demo script chạy 5 queries minh họa hoạt động của HybridMemoryAgent.

Bonus Challenge — Lab 19 (Track 2).
"""
from __future__ import annotations

import sys
from pathlib import Path

# Thêm thư mục gốc vào sys.path
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bonus.agent import HybridMemoryAgent


def main() -> int:
    print("=" * 70)
    print("DEMO: HYBRID AI MEMORY SYSTEM (Vector Store + Feast Feature Store)")
    print("=" * 70)

    # 1. Khởi tạo Agent
    agent = HybridMemoryAgent()
    user_id = "u_001"

    # 2. Nạp một số Episodic Memories mẫu cho user
    sample_memories = [
        "Người dùng đã đọc tài liệu về kiến trúc microservices và triển khai cụm Kubernetes (K8s) trên GCP.",
        "Ghi chú: Cần tối ưu hóa cơ chế tự động co giãn hạ tầng (auto-scaling) và HPA theo lượng request thực tế.",
        "Người dùng đã xem bài viết về bảo mật đám mây, mã hóa dữ liệu lưu trữ và quản lý quyền truy cập IAM.",
        "Tổng kết tuần: Đã nghiên cứu cách tối ưu chi phí hạ tầng Cloud và phân vùng cơ sở dữ liệu theo thời gian.",
    ]
    print(f"[*] Đang nạp {len(sample_memories)} ký ức mẫu cho user {user_id} vào Vector Store...")
    for mem in sample_memories:
        agent.remember(text=mem, user_id=user_id)
    print("[*] Nạp ký ức thành công!\n")

    # 3. Chạy 5 câu truy vấn minh họa
    test_queries = [
        ("Query 1 [Vector Hit]: Hỏi tài liệu đã đọc", "Tôi đã đọc gì về Kubernetes?"),
        ("Query 2 [Profile Context]: Gợi ý chủ đề tiếp theo", "Gợi ý cho tôi nên đọc tài liệu nào tiếp theo?"),
        ("Query 3 [Fresh Activity]: Tra cứu mức độ tương tác gần nhất", "Hôm nay tôi đã tra cứu nhiều không và đang quan tâm gì?"),
        ("Query 4 [Paraphrase Query]: Hỏi dạng diễn đạt lại", "Phương pháp tự động mở rộng và điều chỉnh tài nguyên máy chủ?"),
        ("Query 5 [Mixed Query]: Tóm tắt kết hợp cả Profile và Memories", "Cho tôi tóm tắt kiến thức bảo mật đám mây phù hợp với tôi?"),
    ]

    for idx, (label, q) in enumerate(test_queries, start=1):
        print("-" * 70)
        print(f"TEST {idx}: {label}")
        print(f"Input Query: \"{q}\"")
        context = agent.recall(query=q, user_id=user_id, top_k=2)
        print("\n--- [ASSEMBLED PROMPT CONTEXT] ---")
        print(context)

    print("=" * 70)
    print("DEMO COMPLETED SUCCESSFULLY (All 5 queries executed, Exit 0)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
