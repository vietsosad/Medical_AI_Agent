---
name: medtriage-rag-evidence
description: Implement or audit MedTriage bilingual retrieval, pgvector/sparse fusion, validated-protocol authority checks, calibration, provenance, citation verification, MIETIC demo isolation, and fail-closed evidence behavior. Use for RAG services, evidence tools, protocol ingestion, or citation contracts.
---

# MedTriage RAG Evidence

Treat retrieval relevance and clinical authority as separate gates. A similar
document is not automatically eligible to support ESI.

## Procedure

1. Build Vietnamese, English, and controlled sparse queries from confirmed facts.
2. Retrieve only from the explicitly configured corpus.
3. Validate document type, approval, source authority, scope, metadata, and
   calibrated channel thresholds.
4. Create citations only from accepted source records.
5. Permit ESI reasoning only when evidence status and authority both pass.
6. Fail closed when any required source, criterion, or citation is missing.

Read [references/evidence-contract.md](references/evidence-contract.md) whenever
changing a retriever, evidence gate, reasoner prompt, or citation DTO.
