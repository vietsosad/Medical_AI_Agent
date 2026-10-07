--
-- MedTriage AI -- simple_agent pilot: SCHEMA
--
-- Snapshot of every public.simple_agent_* table (structure only, no rows),
-- exported from the development PostgreSQL 16 + pgvector container on
-- 2026-09-01. Apply this FIRST, then 20260901_simple_agent_corpus_data.sql.
--
-- Precondition: the target database must already contain MedTriage's
-- public.users(id) table -- simple_agent_sessions, simple_agent_chat_sessions
-- and simple_agent_nurse_reviews carry foreign keys to it.
--
-- The four reference tables (clinical_concepts, concept_relations,
-- fact_targets, protocol_atoms) plus fact_target_embeddings hold the clinical
-- decision corpus and are seeded by the companion data file. The four runtime
-- tables (sessions, chat_sessions, chat_messages, nurse_reviews) are created
-- empty; each teammate's own conversations populate them at runtime.
--
-- Setup guide: database/migrations/README.md
--

CREATE EXTENSION IF NOT EXISTS vector;
--
-- PostgreSQL database dump
--


-- Dumped from database version 16.14 (Debian 16.14-1.pgdg12+1)
-- Dumped by pg_dump version 16.14 (Debian 16.14-1.pgdg12+1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: simple_agent_chat_messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.simple_agent_chat_messages (
    id character varying NOT NULL,
    session_id character varying NOT NULL,
    turn_index integer NOT NULL,
    sender character varying NOT NULL,
    content character varying NOT NULL,
    route character varying,
    action character varying,
    question_target_id character varying,
    decision_snapshot json,
    created_at timestamp without time zone NOT NULL,
    channel character varying,
    read_at timestamp without time zone,
    client_message_id character varying
);


--
-- Name: simple_agent_chat_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.simple_agent_chat_sessions (
    id character varying NOT NULL,
    session_id character varying NOT NULL,
    patient_id character varying NOT NULL,
    status character varying NOT NULL,
    turn_count integer NOT NULL,
    initial_message character varying NOT NULL,
    final_route character varying,
    final_action character varying,
    matched_esi_levels json,
    final_message character varying,
    final_concepts json,
    started_at timestamp without time zone NOT NULL,
    last_activity_at timestamp without time zone NOT NULL,
    completed_at timestamp without time zone,
    profile_id character varying
);


--
-- Name: simple_agent_clinical_concepts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.simple_agent_clinical_concepts (
    id character varying NOT NULL,
    concept_id character varying NOT NULL,
    canonical_name character varying NOT NULL,
    aliases json,
    semantic_type character varying NOT NULL,
    embedding public.vector(1536)
);


--
-- Name: simple_agent_concept_relations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.simple_agent_concept_relations (
    id character varying NOT NULL,
    source_concept_id character varying NOT NULL,
    relation_type character varying NOT NULL,
    target_id character varying NOT NULL
);


--
-- Name: simple_agent_fact_target_embeddings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.simple_agent_fact_target_embeddings (
    id character varying NOT NULL,
    fact_target_id character varying NOT NULL,
    embedding_model character varying NOT NULL,
    embedding public.vector(1536)
);


--
-- Name: simple_agent_fact_targets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.simple_agent_fact_targets (
    id character varying NOT NULL,
    fact_target_id character varying NOT NULL,
    name character varying NOT NULL,
    description character varying NOT NULL,
    value_schema json,
    reporting_style character varying NOT NULL,
    lay_terms character varying NOT NULL,
    severity_anchors json,
    gated_by json,
    requires_sex character varying
);


--
-- Name: simple_agent_nurse_reviews; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.simple_agent_nurse_reviews (
    session_id character varying NOT NULL,
    review_status character varying NOT NULL,
    assigned_nurse_id character varying,
    version integer NOT NULL,
    claimed_at timestamp without time zone,
    decision_type character varying,
    decision_reason_code character varying,
    decision_note character varying,
    final_esi integer,
    is_overridden boolean NOT NULL,
    decided_at timestamp without time zone,
    handed_off_at timestamp without time zone,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    parked_at timestamp without time zone,
    parked_by_nurse_id character varying,
    parked_reason character varying
);


--
-- Name: simple_agent_protocol_atoms; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.simple_agent_protocol_atoms (
    id character varying NOT NULL,
    atom_id character varying NOT NULL,
    authority_scope character varying NOT NULL,
    source_document_id character varying NOT NULL,
    atom_type character varying NOT NULL,
    decision_point character varying,
    requirements json,
    decision_effect json,
    retrieval_text character varying NOT NULL,
    retrieval_embedding_model character varying NOT NULL,
    embedding public.vector(1536)
);


--
-- Name: simple_agent_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.simple_agent_sessions (
    id character varying NOT NULL,
    session_id character varying NOT NULL,
    patient_id character varying,
    subject_type character varying NOT NULL,
    subject_label character varying NOT NULL,
    parked_subjects json,
    concepts json,
    concept_order json,
    facts json,
    qualitative_observations json,
    unknown_facts json,
    needs_precision json,
    seen_atom_ids json,
    last_question character varying,
    stale_question_streak integer NOT NULL,
    confirmation_offered boolean NOT NULL,
    resource_count_estimated boolean NOT NULL,
    history json,
    tool_log_tail json,
    created_at timestamp without time zone NOT NULL,
    updated_at timestamp without time zone NOT NULL,
    atom_relevance_score json,
    retrieval_query text,
    card_gender character varying,
    card_relationship character varying
);


--
-- Name: simple_agent_chat_messages simple_agent_chat_messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_chat_messages
    ADD CONSTRAINT simple_agent_chat_messages_pkey PRIMARY KEY (id);


--
-- Name: simple_agent_chat_sessions simple_agent_chat_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_chat_sessions
    ADD CONSTRAINT simple_agent_chat_sessions_pkey PRIMARY KEY (id);


--
-- Name: simple_agent_clinical_concepts simple_agent_clinical_concepts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_clinical_concepts
    ADD CONSTRAINT simple_agent_clinical_concepts_pkey PRIMARY KEY (id);


--
-- Name: simple_agent_concept_relations simple_agent_concept_relations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_concept_relations
    ADD CONSTRAINT simple_agent_concept_relations_pkey PRIMARY KEY (id);


--
-- Name: simple_agent_fact_target_embeddings simple_agent_fact_target_embeddings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_fact_target_embeddings
    ADD CONSTRAINT simple_agent_fact_target_embeddings_pkey PRIMARY KEY (id);


--
-- Name: simple_agent_fact_targets simple_agent_fact_targets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_fact_targets
    ADD CONSTRAINT simple_agent_fact_targets_pkey PRIMARY KEY (id);


--
-- Name: simple_agent_nurse_reviews simple_agent_nurse_reviews_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_nurse_reviews
    ADD CONSTRAINT simple_agent_nurse_reviews_pkey PRIMARY KEY (session_id);


--
-- Name: simple_agent_protocol_atoms simple_agent_protocol_atoms_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_protocol_atoms
    ADD CONSTRAINT simple_agent_protocol_atoms_pkey PRIMARY KEY (id);


--
-- Name: simple_agent_sessions simple_agent_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_sessions
    ADD CONSTRAINT simple_agent_sessions_pkey PRIMARY KEY (id);


--
-- Name: ix_simple_agent_atoms_embedding_hnsw; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_atoms_embedding_hnsw ON public.simple_agent_protocol_atoms USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: ix_simple_agent_chat_messages_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_chat_messages_created_at ON public.simple_agent_chat_messages USING btree (created_at);


--
-- Name: ix_simple_agent_chat_messages_sender; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_chat_messages_sender ON public.simple_agent_chat_messages USING btree (sender);


--
-- Name: ix_simple_agent_chat_messages_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_chat_messages_session_id ON public.simple_agent_chat_messages USING btree (session_id);


--
-- Name: ix_simple_agent_chat_messages_turn_index; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_chat_messages_turn_index ON public.simple_agent_chat_messages USING btree (turn_index);


--
-- Name: ix_simple_agent_chat_sessions_last_activity_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_chat_sessions_last_activity_at ON public.simple_agent_chat_sessions USING btree (last_activity_at);


--
-- Name: ix_simple_agent_chat_sessions_patient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_chat_sessions_patient_id ON public.simple_agent_chat_sessions USING btree (patient_id);


--
-- Name: ix_simple_agent_chat_sessions_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_simple_agent_chat_sessions_session_id ON public.simple_agent_chat_sessions USING btree (session_id);


--
-- Name: ix_simple_agent_chat_sessions_started_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_chat_sessions_started_at ON public.simple_agent_chat_sessions USING btree (started_at);


--
-- Name: ix_simple_agent_chat_sessions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_chat_sessions_status ON public.simple_agent_chat_sessions USING btree (status);


--
-- Name: ix_simple_agent_clinical_concepts_concept_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_simple_agent_clinical_concepts_concept_id ON public.simple_agent_clinical_concepts USING btree (concept_id);


--
-- Name: ix_simple_agent_clinical_concepts_semantic_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_clinical_concepts_semantic_type ON public.simple_agent_clinical_concepts USING btree (semantic_type);


--
-- Name: ix_simple_agent_concept_relations_relation_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_concept_relations_relation_type ON public.simple_agent_concept_relations USING btree (relation_type);


--
-- Name: ix_simple_agent_concept_relations_source_concept_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_concept_relations_source_concept_id ON public.simple_agent_concept_relations USING btree (source_concept_id);


--
-- Name: ix_simple_agent_concept_relations_target_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_concept_relations_target_id ON public.simple_agent_concept_relations USING btree (target_id);


--
-- Name: ix_simple_agent_concepts_embedding_hnsw; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_concepts_embedding_hnsw ON public.simple_agent_clinical_concepts USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: ix_simple_agent_fact_target_embeddings_fact_target_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_simple_agent_fact_target_embeddings_fact_target_id ON public.simple_agent_fact_target_embeddings USING btree (fact_target_id);


--
-- Name: ix_simple_agent_fact_target_embeddings_hnsw; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_fact_target_embeddings_hnsw ON public.simple_agent_fact_target_embeddings USING hnsw (embedding public.vector_cosine_ops) WITH (m='16', ef_construction='64');


--
-- Name: ix_simple_agent_fact_targets_fact_target_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_simple_agent_fact_targets_fact_target_id ON public.simple_agent_fact_targets USING btree (fact_target_id);


--
-- Name: ix_simple_agent_fact_targets_reporting_style; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_fact_targets_reporting_style ON public.simple_agent_fact_targets USING btree (reporting_style);


--
-- Name: ix_simple_agent_nurse_reviews_assigned_nurse_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_nurse_reviews_assigned_nurse_id ON public.simple_agent_nurse_reviews USING btree (assigned_nurse_id);


--
-- Name: ix_simple_agent_nurse_reviews_review_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_nurse_reviews_review_status ON public.simple_agent_nurse_reviews USING btree (review_status);


--
-- Name: ix_simple_agent_protocol_atoms_atom_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_simple_agent_protocol_atoms_atom_id ON public.simple_agent_protocol_atoms USING btree (atom_id);


--
-- Name: ix_simple_agent_protocol_atoms_atom_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_protocol_atoms_atom_type ON public.simple_agent_protocol_atoms USING btree (atom_type);


--
-- Name: ix_simple_agent_protocol_atoms_authority_scope; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_protocol_atoms_authority_scope ON public.simple_agent_protocol_atoms USING btree (authority_scope);


--
-- Name: ix_simple_agent_protocol_atoms_decision_point; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_protocol_atoms_decision_point ON public.simple_agent_protocol_atoms USING btree (decision_point);


--
-- Name: ix_simple_agent_sessions_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_sessions_created_at ON public.simple_agent_sessions USING btree (created_at);


--
-- Name: ix_simple_agent_sessions_patient_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_simple_agent_sessions_patient_id ON public.simple_agent_sessions USING btree (patient_id);


--
-- Name: ix_simple_agent_sessions_session_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_simple_agent_sessions_session_id ON public.simple_agent_sessions USING btree (session_id);


--
-- Name: simple_agent_chat_sessions simple_agent_chat_sessions_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_chat_sessions
    ADD CONSTRAINT simple_agent_chat_sessions_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.users(id);


--
-- Name: simple_agent_nurse_reviews simple_agent_nurse_reviews_assigned_nurse_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_nurse_reviews
    ADD CONSTRAINT simple_agent_nurse_reviews_assigned_nurse_id_fkey FOREIGN KEY (assigned_nurse_id) REFERENCES public.users(id);


--
-- Name: simple_agent_nurse_reviews simple_agent_nurse_reviews_session_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_nurse_reviews
    ADD CONSTRAINT simple_agent_nurse_reviews_session_id_fkey FOREIGN KEY (session_id) REFERENCES public.simple_agent_chat_sessions(session_id);


--
-- Name: simple_agent_sessions simple_agent_sessions_patient_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.simple_agent_sessions
    ADD CONSTRAINT simple_agent_sessions_patient_id_fkey FOREIGN KEY (patient_id) REFERENCES public.users(id);


--
-- PostgreSQL database dump complete
--


