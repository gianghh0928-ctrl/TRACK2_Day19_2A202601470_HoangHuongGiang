# Architecture Design: Personal AI Assistant Hybrid Memory System

**Tác giả:** Hoàng Hương Giang (Cohort A20-K2)  
**Mục tiêu:** Thiết kế và xây dựng Proof-of-Concept (POC) kiến trúc bộ nhớ lai (Hybrid Memory Architecture) cho trợ lý AI cá nhân tại Việt Nam, kết hợp **Vector Store** (Episodic Memory) và **Feature Store** (Stable Profile & Streaming Activity).

---

## 1. Sơ đồ Kiến trúc Tổng thể (System Architecture)

Hệ thống phân tách rõ ràng luồng dữ liệu giữa ký ức ngữ cảnh dài hạn, thông tin hồ sơ tĩnh và hoạt động theo thời gian thực:

```mermaid
flowchart TD
    subgraph Client ["Client & User Interaction"]
        U["Người dùng (User)"]
        APP["AI Assistant Interface"]
    end

    subgraph MemoryLayer ["Hybrid Memory Layer (bonus/agent.py)"]
        HMA["HybridMemoryAgent"]
        INGEST["remember(text, user_id)"]
        RETRIEVE["recall(query, user_id)"]
    end

    subgraph StorageEngine ["Dual Storage Infrastructure"]
        subgraph EpisodicStore ["1. Episodic Memory (Vector DB - Qdrant)"]
            EMB["FastEmbed / BGE Embedding"]
            QDRANT[("Qdrant Collection\nlab19_bonus_memory\nPayload: user_id, timestamp, text")]
        end

        subgraph ProfileStore ["2. Feature Store (Feast)"]
            ONLINE_SQLITE[("SQLite Online Store\n- user_profile_features\n- query_velocity_features")]
            OFFLINE_PARQUET[("Offline Parquet Data Warehouse")]
        end
    end

    subgraph AssemblyContext ["Context Assembly Engine"]
        CTX_BUILDER["Prompt Context Builder"]
        LLM["LLM Response Generation"]
    end

    U -->|1. Gửi ghi chú / hội thoại mới| APP
    APP -->|remember()| INGEST
    INGEST -->|Chunking & Embedding| EMB
    EMB -->|Upsert Point with user_id filter| QDRANT

    U -->|2. Đặt câu hỏi / Tra cứu| APP
    APP -->|recall()| RETRIEVE
    RETRIEVE -->|Filtered Vector Search (user_id)| QDRANT
    RETRIEVE -->|get_online_features (user_id)| ONLINE_SQLITE
    OFFLINE_PARQUET -.->|materialize-incremental| ONLINE_SQLITE

    QDRANT -->|Top-K Episodic Matches| CTX_BUILDER
    ONLINE_SQLITE -->|Profile & Velocity Features| CTX_BUILDER
    CTX_BUILDER -->|Assembled System & User Context| LLM
    LLM -->|Trả lời cá nhân hóa| U
```

---

## 2. Ba Quyết định Kiến trúc & Phân tích Tradeoff (Architecture Decisions & Tradeoffs)

### Quyết định 1: Chiến lược Phân đoạn Ký ức (Chunking Strategy)
* **Lựa chọn:** *Semantic Sliding Window* (Kích thước 256 tokens, overlap 32 tokens) kết hợp lưu trữ metadata cấp độ đoạn văn.
* **So sánh Tradeoff (Semantic Window vs Per-Message Chunking):**
  * *Per-Message Chunking (Từng tin nhắn đơn lẻ):* Rất đơn giản để cài đặt, nhưng làm mất ngữ cảnh nếu người dùng chia nhỏ ý ra nhiều tin nhắn liên tiếp (ví dụ: tin 1: "Tôi vừa chuyển sang dùng GCP", tin 2: "Cụ thể là Cloud Run"). Khi tìm kiếm, tin 2 sẽ không có đủ ngữ nghĩa về GCP.
  * *Semantic Sliding Window:* Đảm bảo tính toàn vẹn ngữ nghĩa xuyên suốt các lượt hội thoại, giảm thiểu hiện tượng đứt gãy thông tin khi truy vấn. Mặc dù chi phí tính toán embedding và dung lượng lưu trữ tăng khoảng 15-20% do phần chồng lấn (overlap), nhưng chất lượng retrieval cải thiện rõ rệt, đặc biệt trong các tác vụ tổng hợp ký ức dài hạn.

### Quyết định 2: Mô hình Schema cho Hồ sơ Người dùng (Feature Schema Design)
* **Lựa chọn:** *Tabular Key-Value Profile* kết hợp *Streaming Velocity Counters* trong Feast Feature Store (thay vì dùng Latent Preference Embedding Vectors).
* **So sánh Tradeoff (Tabular Explicit Schema vs Latent Embedding Profile):**
  * *Latent Embedding Profile (Vector biểu diễn sở thích người dùng):* Nén toàn bộ lịch sử thành 1 vector duy nhất. Tuy nhiên, phương pháp này như một "hộp đen" (black box), rất khó debug khi LLM đưa ra câu trả lời sai lệch, và tốn kém chi phí suy luận vector.
  * *Tabular Explicit Schema (`reading_speed_wpm`, `topic_affinity`, `queries_last_hour`):* Thời gian truy xuất siêu nhanh ($< 2\text{ ms}$ trên Online Store), có thể kiểm tra trực tiếp (deterministic) và dễ dàng kiểm soát quyền riêng tư (người dùng có thể xem và chỉnh sửa trực tiếp hồ sơ của mình).

### Quyết định 3: Chiến lược Làm tươi Dữ liệu (Data Freshness & Materialization Strategy)
* **Lựa chọn:** *Chiến lược Đa tầng (Tiered Freshness)* dựa trên đặc tính của từng nhóm feature:
  * **Ký ức hội thoại (Episodic Memory):** Cập nhật thời gian thực (Real-time sub-second) vào Qdrant ngay khi hội thoại kết thúc.
  * **Tần suất hoạt động (`query_velocity_features`):** Cập nhật định kỳ 5 phút một lần hoặc qua streaming push API để phát hiện xu hướng tập trung hiện tại của người dùng.
  * **Hồ sơ tĩnh (`user_profile_features`):** Cập nhật dạng Batch hàng ngày (Daily Batch Materialization) vì sở thích dài hạn và tốc độ đọc của người dùng ít khi thay đổi đột ngột.
* **Tradeoff:** Tiết kiệm hơn 80% chi phí tính toán và I/O so với việc bắt toàn bộ hệ thống phải đồng bộ realtime 100%, trong khi vẫn đảm bảo trải nghiệm tức thì đối với các ký ức mới nạp.

---

## 3. Lựa chọn Bị loại bỏ và Lý do (Rejected Alternative)

* **Phương án xem xét:** Lưu trữ toàn bộ Episodic Memory (toàn bộ văn bản hội thoại) trực tiếp vào Feature Store dưới dạng String Features hoặc Blob.
* **Lý do loại bỏ:** 
  1. *Khác biệt về chu kỳ truy vấn (Access Pattern Mismatch):* Feature Store được tối ưu hóa cho truy xuất theo Key chính xác (`entity_key = user_id`) trong thời gian cực ngắn. Feature Store không có cấu trúc chỉ mục HNSW hay Inverted Index để thực hiện tìm kiếm mờ (fuzzy search), tìm kiếm tương đồng vector hoặc lọc ngữ nghĩa (similarity ranking).
  2. *Chi phí và Chu kỳ Re-index:* Episodic Memory tăng liên tục theo từng phút, trong khi Feature Store Registry được thiết kế cho các bảng dữ liệu có cấu trúc ổn định. Tách riêng Vector Store (Qdrant) cho episodic text và Feature Store (Feast) cho user metrics là kiến trúc chuẩn mực của RAG Production.

---

## 4. Cân nhắc Đặc thù Ngữ cảnh Tiếng Việt (Vietnamese-Context Considerations)

1. **Xử lý Hiện tượng Code-Switching (Pha trộn Anh - Việt):** Trong lĩnh vực công nghệ tại Việt Nam, người dùng thường xuyên kết hợp thuật ngữ tiếng Anh và cấu trúc tiếng Việt (ví dụ: *"Deploy app lên Kubernetes bị lỗi crash loop"*). Việc sử dụng Hybrid Search (BM25 bắt các từ mượn tiếng Anh như *Kubernetes, crash loop*, Vector bắt ngữ cảnh câu hỏi tiếng Việt) giúp khắc phục triệt để nhược điểm của các mô hình nhúng đơn ngữ.
2. **Xử lý Từ ghép và Dấu thanh:** Tiếng Việt có đặc trưng từ ghép đa âm tiết (ví dụ: *"tự động mở rộng"* gồm 4 âm tiết nhưng là 1 cụm khái niệm). Cần áp dụng chuẩn hóa Unicode NFC và cơ chế tokenization phù hợp để tránh lỗi đứt đoạn từ khóa khi lập chỉ mục BM25.
3. **Tuân thủ Quyền riêng tư & Dữ liệu cá nhân (Nghị định 13/2023/NĐ-CP):** Dữ liệu bộ nhớ cá nhân phải được phân vùng độc lập (Namespace / Payload Filter theo `user_id`), cho phép người dùng thực hiện quyền xem, xuất và xóa dữ liệu ký ức (Right to be Forgotten) một cách minh bạch.

---

## 5. Hạn chế Thực tế của Bản POC (Limitations & Future Work)

Bản POC hiện tại tập trung chứng minh tính khả thi của việc ghép nối ngữ cảnh giữa Vector Store và Feature Store, do đó chưa bao gồm một số tính năng mở rộng:
* **Mã hóa dữ liệu tại chỗ (Encryption at Rest):** Chưa tích hợp mã hóa từng collection theo khóa riêng của từng user.
* **Cơ chế Quên / Suy giảm Ký ức (Memory Decay & Pruning):** Chưa cài đặt thuật toán giảm trọng số theo thời gian (exponential decay) cho các ký ức cũ không được truy cập quá 90 ngày.
* **Hợp nhất Ký ức (Memory Consolidation):** Chưa có background worker tự động tóm tắt 10 cuộc hội thoại nhỏ trong tuần thành 1 bản tóm tắt ký ức cốt lõi.
