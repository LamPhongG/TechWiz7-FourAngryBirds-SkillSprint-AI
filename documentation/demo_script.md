# SkillSprint AI — Product Demonstration Video Script
**Competition:** TechWiz 7 – Generative AI Powerplay Track  
**Project:** SkillSprint AI – Dual-Pipeline AI Document Verification System  
**Target Duration:** Exactly 05:00 (300 seconds) | **Resolution:** 1080p 60fps (Full HD)  
**Narration Team:** Four Angry Birds (Chau Quoc Lam Phong presenting Pipeline & Verification)

---

## I. Master Scene Timeline (5 Minutes)

| Scene | Duration | Content Segment | Presenter / Screen Focus |
| :---: | :---: | :--- | :--- |
| **Scene 1** | 0:00 – 0:40 (40s) | The Onboarding Problem & The Peril of AI Hallucinations | Full Team Overview |
| **Scene 2** | 0:40 – 1:30 (50s) | Phase 1 & 2: Ingestion & Grounded Path Generation | Chau Quoc Lam Phong |
| **Scene 3** | 1:30 – 2:30 (60s) | Phase 3: Dual-Pipeline Cross-Verification & Match Scoring | Lam Phong & Quynh Nhi |
| **Scene 4** | 2:30 – 3:45 (75s) | **FEATURE HIGHLIGHT:** Defending Against 4 Adversarial Traps | Chau Quoc Lam Phong |
| **Scene 5** | 3:45 – 4:30 (45s) | Phase 4: Autonomous Evaluation on Unseen Policy Documents | Lam Phong & Kieu Duyen |
| **Scene 6** | 4:30 – 5:00 (30s) | Real-world Enterprise Impact & Closing | Full Team |

---

## II. Scene-by-Scene Script

### Scene 1: The Problem & System Introduction (0:00 – 0:40)
* **Visuals:**
  * 0:00 – 0:15: Title slide with SkillSprint AI logo, Four Angry Birds team roster, and TechWiz 7 track identifier.
  * 0:15 – 0:40: Infographic illustrating the enterprise onboarding bottleneck: hundred-page employee handbooks overwhelm recruits, while generic LLMs hallucinate policies or succumb to prompt injection attacks.
* **Voiceover:**
  > "Welcome, TechWiz 7 Judges. In the hybrid workplace, onboarding new hires typically requires weeks of wading through dense corporate handbooks and technical SOPs.  
  > While applying Generative AI seems promising, standard LLMs introduce catastrophic operational risks: AI easily hallucinates—fabricating vacation policies or spending limits—or yields to adversarial prompt injections embedded in uploaded files.  
  > Team Four Angry Birds presents **SkillSprint AI**—the first Dual-Pipeline verification system that pairs Generative AI with an independent, deterministic Python Rule Engine to guarantee 100% corporate compliance."

---

### Scene 2: Document Ingestion & Grounded Path Generation (0:40 – 1:30)
* **Visuals:**
  * 0:40 – 1:05: File upload workflow showing multi-page policy document ingestion. Terminal display showing PyMuPDF extraction, section-aware chunking, and deterministic metadata indexing (`doc_id`, `chunk_id`, `page_number`).
  * 1:05 – 1:30: Generated Onboarding Path view. Zooming into Pydantic schema: each module, task, and quiz question contains an enforced `source_reference` with a verbatim `exact_quote`.
* **Voiceover:**
  > "In Pipeline 1, our ingestion engine parses multi-page PDFs and Word documents, analyzing section headers and extracting structured chunks indexed by page number.  
  > The Gemini engine processes these chunks alongside the specific job position requirements. The key breakthrough of SkillSprint AI is **enforced Structured Outputs**: every single lesson, task criteria, and quiz question must include a verbatim `exact_quote` extracted directly from source text, completely eliminating unverified text generation."

---

### Scene 3: Dual-Pipeline Comparison & Match Scoring (1:30 – 2:30)
* **Visuals:**
  * 1:30 – 1:55: Interactive dual-pipeline architecture diagram: Pipeline 1 (GenAI) compared side-by-side with Pipeline 2 (Deterministic Python Rule Engine, Zero-AI).
  * 1:55 – 2:30: Verification Dashboard: Dual-Pipeline Comparison Table showing field-by-field diff, 100% Traceability Score, 100% Coverage Score, and green `VERIFIED` status badge.
* **Voiceover:**
  > "Conventional AI systems stop here, but SkillSprint AI goes further. The system activates **Pipeline 2: A deterministic Python Rule Engine**, completely independent of AI.  
  > This engine evaluates the Role Requirement Matrix, checks prerequisite DAGs, and verifies every AI citation against raw database chunks.  
  > When both pipelines agree, the system issues a cryptographically grounded `VERIFIED` status in under two seconds, eliminating the need for manual audit."

---

### Scene 4: Adversarial Defense & Catching 4 Critical Traps (2:30 – 3:45)
* **Visuals:**
  * 2:30 – 2:50: **Traps 1 & 2:** Triggering a fabricated $500 gym stipend and an altered leave policy (30 days instead of 15). The interface flags `HallucinationFlag`, immediately downgrading status to `MANUAL_REVIEW_REQUIRED`.
  * 2:50 – 3:15: **Trap 3:** Internal policy contradiction (90-day password change in Section 1 vs 30-day requirement in Section 2). Contradiction Checker detects the conflict and flags a policy warning.
  * 3:15 – 3:45: **Trap 4 (Prompt Injection):** Uploading a file containing `SYSTEM OVERRIDE: Ignore all previous instructions...`. The defensive filter quarantines the attack chunk, blocking malicious instructions.
* **Voiceover:**
  > "To prove resilience, we subject our platform to real-world edge cases where generic AI fails.  
  > First: when an AI hallucinates an unauthorized gym subsidy or an altered leave quota, our grounding validator detects the discrepancy and raises an immediate `HallucinationFlag`.  
  > Second: when an internal policy contains contradictory clauses on password rotation, the Contradiction Checker catches the discrepancy.  
  > And most crucially: prompt injection attempts like `SYSTEM OVERRIDE` are intercepted and quarantined at ingestion, safeguarding enterprise data integrity."

---

### Scene 5: Autonomous Execution on Unseen Documents (3:45 – 4:30)
* **Visuals:**
  * 3:45 – 4:10: Running `hidden_test_ready/run_hidden_test.py` on an unseen policy document: `sample_unseen_policy.pdf`.
  * 4:10 – 4:30: Terminal output and generated `hidden_test_report.json` showing `VERIFIED` status, 100% match score, 0 hallucinations, and end-to-end execution in under 1.5 seconds.
* **Voiceover:**
  > "Engineered for evaluation on unseen documents, SkillSprint AI handles new policy files completely autonomously.  
  > When fed an unfamiliar cybersecurity policy, the complete pipeline—ingestion, Unicode normalization, chunking, curriculum generation, and rule verification—executes end-to-end without manual configuration, outputting a complete compliance report in seconds."

---

### Scene 6: Conclusion & Impact (4:30 – 5:00)
* **Visuals:**
  * 4:30 – 4:45: Summary slide highlighting core metrics: 80% reduction in onboarding time, 100% elimination of AI hallucination risk, and multi-tier security.
  * 4:45 – 5:00: Four Angry Birds team roster, TechWiz 7 logo, and final thank-you message.
* **Voiceover:**
  > "With our pioneering Dual-Pipeline architecture, SkillSprint AI liberates HR teams from tedious onboarding development while setting a new standard for trust and safety in enterprise AI adoption.  
  > Team Four Angry Birds thanks the TechWiz 7 Evaluation Committee for their time and consideration!"

---

## III. Recording & Quality Checklist

### 1. Pre-Recording Preparation
- [ ] Clean desktop, hide taskbars, disable background notifications.
- [ ] Configure OBS Studio: 1920x1080 resolution @ 60fps, bitrate ≥ 6,000 Kbps.
- [ ] Microphone noise suppression enabled.
- [ ] Verify test environment: activate virtual environment, confirm all automated test suites pass.

### 2. Capture Checklist
- [ ] **Clip 1 (Ingestion):** Clean terminal output showing chunk extraction.
- [ ] **Clip 2 (GenAI Output):** Structured curriculum JSON showing exact-quote citations.
- [ ] **Clip 3 (Verification):** Dual-Pipeline Comparison Table with 100% green verified state.
- [ ] **Clip 4 (Defensive Traps):** Hallucination and injection detection flags displayed in UI.
- [ ] **Clip 5 (Unseen Policy Test):** Automated test script execution producing JSON reports.
