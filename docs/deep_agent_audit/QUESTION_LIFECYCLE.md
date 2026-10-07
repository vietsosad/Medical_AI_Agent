# QUESTION LIFECYCLE — semantic identity, binding, resolution

*What a question is, how its answer gets attached to it, and what stops it from
being asked twice.*

---

## 1. A question's stable identity

Every question the agent asks carries a **semantic target**, not a sentence.
Targets have exactly three shapes:

| Shape | Example | Answer lands on |
|---|---|---|
| problem attribute | `headache.worst_ever`, `headache.course` | `headache.worst_ever` (entity-scoped) |
| shared symptom probe | `symptom.fever`, `symptom.syncope` | `symptom.fever` |
| objective measurement | `vital.temperature_c`, `vital.spo2` | `vital.temperature_c` |
| *(legacy)* workflow slot | `onset_time`, `severity_score`, `vital_signs`, `clinical_memory_confirmation` | the same global key |

Wording lives in `adaptive_questions._ATTRIBUTE_QUESTIONS` / `_VITAL_QUESTIONS`
and is chosen *after* the target. Two different sentences for one target are
therefore the same question — which is what makes dedupe semantic rather than
textual (§9).

## 2. The lifecycle, as it runs

```
question_planning.collect_candidates
   reads ProblemState → every unanswered relevant attribute
   scores it (importance × primary/new-problem bonus × uncertainty nudge)
   drops targets already asked `max_repeats_per_target` times
        ↓
readiness_evaluator: top-N candidates become `missing_critical_fields`
   and their gains become `target_information_gain`
        ↓
next_best_action.select_next_best_action
   safety precedence first; then contradictions; then ASK max-by-gain
        ↓
action_validator.plan_and_validate      ← may block or replace
        ↓
action_planner: asked_targets[target] += 1
                consecutive_questions += 1   (clinical targets only)
        ↓
action_execution._execute_ask → question_engine.run_question_engine_node
   renders the target, records `active_question`
   {field, question_id, question_type, semantic_target, options_type}
        ↓
── patient replies ──
        ↓
answer_validator.validate_answer_alignment(query, active_question)
   an adaptive target accepts any substantive reply, including "tôi không biết"
        ↓
intake_analyzer
   1. every extractor runs on the message (facts the patient volunteers)
   2. if the reply did not already answer the asked target,
      problem_attribute_extraction.extract_answer_for_target binds it to the
      target's canonical key
        ↓
canonical fact recorded (KNOWN | NEGATED | UNCERTAIN+declined_unknown)
        ↓
problem_state: ProblemFactState.is_answered → True
        ↓
collect_candidates no longer emits the target
```

## 3. What counts as answered

| Reply | Recorded as | Re-asked? |
|---|---|---|
| "Không, không phải" | `NEGATED` | no — a denial is an answer |
| "Từ sáng nay" | `KNOWN` | no |
| "Tôi không biết" | `UNCERTAIN` + `note=declined_unknown` | no — settled conversationally |
| "Hình như có" | `UNCERTAIN` (no note) | once — a hedge is worth one clarification |
| a reply that introduces a new symptom instead | not bound to the target | yes, once more |
| a reply longer than 160 chars | not bound (it is a narrative) | yes, once more |

`extract_answer_for_target` refuses to bind free text to a boolean target
(`symptom.*`, `worst_ever`, `associated_neuro`, …). "Tôi không có nhiệt kế"
answering "do you also have vomiting?" must not become a vomiting finding.

## 4. Re-asking, and how it is marked

A target may be put to the patient at most **twice** (`MAX_REPEATS_PER_TARGET`).
The second time is now explicitly a clarification:

* `active_question.question_type = "CLARIFICATION"`;
* the wording is prefixed with *"Mình chưa rõ ý này nên hỏi lại một chút."*

Before the audit the repeat was **byte-identical** to the first ask
(`identical_text_repeat_rate` 0.17 in the baseline), which reads as the agent
having forgotten rather than having failed to understand.

After two asks the target moves to `accepted_unknown_targets` and is never
selected again. It is recorded as unknown; nothing is invented.

## 5. Where the lifecycle still leaks

| Leak | Effect | Status |
|---|---|---|
| `asked_targets` lived only in process memory | a restart could re-ask an answered-by-declining question | **fixed** — persisted in `TriageCase.conversation_control` |
| `active_question` for a free-text adaptive target has no structured payload | message-replay recovery cannot rebuild it after a cold start | open (F-07); mitigated by durable control state |
| the reasoner's own `evidence_requested_fact` re-enters the legacy slot ladder | question wording drops back to global slots | partly fixed — global slots now name the primary problem when the case has more than one |
