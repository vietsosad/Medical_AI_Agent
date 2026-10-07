---
name: clinical-rag-guardrails
description: Production patterns for Medical Hybrid RAG (ChromaDB + BM25 keyword retrieval + SQLAlchemy PostgreSQL), strict LLM response validation, and dual-layer AI safety guardrails. Use when designing embeddings, RAG retrievers, system prompts, output parsers, or emergency detection rules.
---

# Clinical Hybrid RAG & Medical AI Guardrails

This skill prescribes enterprise patterns and clinical safety rules for constructing reliable RAG (Retrieval-Augmented Generation) architectures and AI guardrails within healthcare chatbot engines and medical triage workflows.

## 1. Hybrid RAG Strategy (Dense Vectors + Sparse Keywords)

Pure vector embeddings frequently miss precise medical acronyms, explicit dosage numbers, or numerical vital sign thresholds (e.g., "SpO2 <= 89%", "BP < 90/60", "GCS 8"). To achieve high concordance with established medical guidelines, implement **Hybrid Retrieval**:

1. **Dual-Index Search**:
   - **Dense Semantic Retrieval (ChromaDB)**: Searches high-dimensional vector embeddings to capture semantic symptom equivalents and patient colloquialisms (e.g., mapping "đau ngực như có đá đè" to "Myocardial Infarction symptoms").
   - **Sparse Keyword Retrieval (BM25 / Postgres Full-Text Search)**: Searches exact diagnostic terminology and clinical protocol thresholds (e.g., "ESI Level 2 criteria", "Triage Guideline A2").
2. **Recalibration & Reranking**:
   - Merge search results from both retrievers using Reciprocal Rank Fusion (RRF) or dedicated reranking algorithms to present the most authoritative clinical protocol chunk to the reasoning node.

## 2. Dual-Layer Medical Safety Shield (The <50ms Mandate)

In clinical triage applications, delayed or hallucinated responses to life-threatening conditions (e.g., cardiac arrest, anaphylaxis, active stroke) carry fatal liability. Implement a strict dual-layer firewall architecture:

### Layer 1: Reflex Emergency Shield (<50ms Deterministic Interception)
- Before initiating any LLM completion or LangGraph reasoning chain, every incoming user utterance must be evaluated by a deterministic, regular-expression and rule-based screening engine (`RedFlagDetector`).
- **Trigger Condition**: Detection of acute life-threatening expressions ("đau thắt ngực", "khó thở dữ dội", "ngất xỉu", "chảy máu không cầm", "liệt nửa người", "mất trí giác").
- **Action**: Immediately halt normal conversation flow (<50ms latency). Override AI response generation, inject an emergency triage flag into the nurse WebSocket channel, and render an explicit SOS emergency telephone Call-to-Action (`tel:115`) on the user interface.

### Layer 2: Output Firewall & Diagnosis Suppression
- An automated interceptor must scan all raw output text synthesized by LLM reasoning nodes before transmitting completions to the client interface.
- **Strict Prohibition**: The system must never assert explicit medical diagnoses ("Bạn đã bị ung thư / nhồi máu cơ tim") or prescribe prescription pharmaceutical regimens.
- **Transformation**: Convert assertions into objective clinical observations and actionable recommendations (e.g., "Dựa trên các triệu chứng bạn mô tả như X và Y, đây là dấu hiệu cần được bác sĩ chuyên khoa kiểm tra gấp...").

## 3. RAG Provenance & Zero-Hallucination Enforcements

1. **Mandatory Protocol Citation**:
   - Whenever an AI agent calculates an Emergency Severity Index (ESI Level 1 to 5) or generates an SBAR Clinical Handoff card, it must explicitly tie its reasoning to retrieved documentation chunks from the RAG database.
   - Format citation artifacts consistently: `[Ref: Protocol ESI-2 / Cardiac Emergencies - Section 3.2]`.
2. **Strict Fallback Protocol**:
   - If the hybrid retrieval engine fails to uncover relevant medical protocols with sufficient similarity score thresholds, the AI reasoning node MUST decline to invent arbitrary clinical thresholds. It should resort to safe conservative defaults (escalating to a higher ESI level or scheduling human nursing interaction).

## 4. Structured Output Parsing (Pydantic Outlets)

- Instruct LLM generators to produce strict structured outputs (JSON schema conforming to Pydantic models) rather than unstructured markdown paragraphs when communicating with internal backend nodes or database checkpointers.
- Utilize structured parsers (e.g., LangChain's `PydanticOutputParser` or native LLM function calling / structured JSON mode) to guarantee type-safe integration with frontend dashboards and medical database schemas.
