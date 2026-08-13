# Multi-Layer Guardrails for Clinical RAG Question Answering

## Research Question / Problem Statement

Large Language Model (LLM) applications are increasingly being explored for clinical question-answering (QA), where healthcare professionals can ask natural-language questions about patient records, diagnoses, medications, admissions, and treatment patterns. Retrieval-Augmented Generation (RAG) is commonly used in this setting because the model can answer from retrieved clinical records rather than relying only on its general training data.

However, clinical QA systems introduce serious safety, privacy, and reliability risks. Patient records may contain sensitive health information, and a poorly protected LLM system may expose identifiers, follow malicious instructions, retrieve irrelevant records, or produce unsupported clinical claims. These risks are especially important in healthcare because the users may rely on the system for clinical decision support, and patients expect their data to remain confidential.

This project focuses on a clinical QA prototype that retrieves patient history records from a ChromaDB vector database and uses an LLM to generate answers for healthcare-style questions. The system is protected by a configurable multi-layer guardrail framework that checks the user input, retrieved context, generated output, and session behaviour.

The central problem is that a normal RAG pipeline is not enough for clinical QA. The system must also protect against prompt injection, jailbreak attempts, indirect attacks hidden in retrieved records, and leakage of personally identifiable information (PII) or protected health information (PHI). It must do this without damaging legitimate clinical questions, such as questions about asthma medication, admissions, diagnoses, or treatment summaries.

**Main research question:**

How effective is a configurable multi-layer guardrail framework in improving the safety, privacy, and reliability of a clinical RAG-based QA system while preserving useful answers for healthcare professionals?

**Sub-questions:**

1. How well do the guardrail layers detect and reduce prompt injection, jailbreak, PII leakage, and unsafe clinical outputs?
2. How do input redaction, output scanning, and retrieval filtering affect clinical QA accuracy and usability?
3. Does a layered guardrail architecture provide stronger protection than a single filtering layer in a clinical RAG workflow?
4. What trade-offs arise between privacy protection and retrieval quality when clinical identifiers are detected or redacted?

This research is significant because clinical LLM systems must balance two competing needs: they must retrieve enough relevant information to answer clinical questions, but they must also prevent unnecessary exposure of patient identifiers and unsafe model behaviour.

## Intended Users / Stakeholders and Needs

The primary users of the proposed system are healthcare professionals, such as doctors, nurses, and clinical administrators, who need to ask questions over patient history data. Example questions include:

- What medication is used to treat asthma?
- How many patients had abnormal test results?
- What admission types are associated with diabetes?
- Which medications appear in records for infections?

These users need accurate, grounded answers based only on retrieved clinical records. They also need the system to avoid hallucinating information when the retrieved context does not support an answer.

Patients are indirect but important stakeholders. Their records may contain names, admission dates, conditions, medications, hospitals, doctors, and other sensitive information. Patients need assurance that the system does not unnecessarily expose identifiers or allow unauthorised extraction of confidential data.

System administrators and security teams are also stakeholders. They need a practical way to configure guardrail rules, inspect safety behaviour, and update policies without changing application code. For this reason, the project includes a guardrail administration UI for viewing and editing `guardrails.yaml`.

The project therefore aims to support three stakeholder needs:

- clinical usefulness for healthcare-style QA;
- privacy protection for patient data;
- manageable configuration for administrators.

## Project Scope, Deliverables and Expected Outcomes

The project scope is a working clinical QA prototype using a healthcare dataset stored in ChromaDB. The backend is implemented with FastAPI, and the RAG pipeline retrieves relevant patient records before calling an LLM to generate an answer. The system includes a separate guardrail SDK and user interfaces for demonstrating the clinical QA flow and editing guardrail rules.

The main deliverables are:

- A clinical RAG QA backend using FastAPI, ChromaDB, and an LLM API.
- A demo UI that allows users to ask clinical questions and inspect guardrail stages.
- A guardrail administration UI for managing `guardrails.yaml`.
- A configurable six-layer guardrail framework:
  - L1: Input normalisation and deterministic input redaction.
  - L2: Intent classification for prompt injection, jailbreak, harmful content, PII exfiltration, and denial-of-service style requests.
  - L3: System prompt hardening for clinical QA.
  - L4: RAG context sanitisation to detect malicious content inside retrieved records.
  - L5: Output scanning for harmful content, PII/PHI leakage, NER-style entity redaction, and canary-token exposure.
  - L6: Session tracking and rate limiting.
- Clinical retrieval improvements, including condition-based filtering for questions mentioning conditions such as Asthma, Flu, Diabetes, Cancer, Heart Disease, Infections, Obesity, or Alzheimer’s.
- Input-side identifier handling, such as redacting explicit patient IDs before the question is sent to the LLM.
- Output-side PII and NER-style redaction for sensitive entities when enabled.
- Basic Auth protection for the guardrail administration UI.
- Automated tests for guardrail behaviours such as patient ID redaction, admission-date preservation, and output redaction.

The expected outcome is a clinical QA system that can answer useful healthcare-style questions from patient records while showing measurable improvement in privacy and security compared with an unguarded RAG pipeline.

## Research Methodology

This project will use a design-and-evaluation methodology. First, a clinical RAG QA prototype will be implemented. The system will retrieve patient records from ChromaDB and generate answers using an LLM. The prompt will instruct the model to answer only from retrieved context and to state when the context is insufficient.

Second, a multi-layer guardrail SDK will be integrated into the application. The layers will be configurable through `guardrails.yaml`, allowing the system administrator to adjust thresholds, enabled checks, output scanning settings, and rule patterns.

Third, the system will be evaluated using both benign clinical questions and adversarial prompts. Benign questions will test whether the system can answer normal clinical QA tasks, such as medication lookup by condition. Adversarial prompts will test prompt injection, jailbreak attempts, encoded attacks, indirect context injection, and PII leakage.

The evaluation will consider:

- attack detection and blocking rate;
- false positives on legitimate clinical questions;
- whether sensitive identifiers are redacted appropriately;
- whether retrieval remains accurate after input sanitisation;
- response latency and usability impact;
- quality of grounded clinical answers.

The evaluation will compare guarded and less-guarded configurations to understand how much each layer contributes to system safety.

## Initial Literature Review

Existing research shows that LLM systems are vulnerable to prompt injection, jailbreaks, and data-exfiltration attempts. These risks are more serious in RAG systems because malicious instructions can enter not only through the user prompt but also through retrieved documents. In clinical QA, the risk is amplified because retrieved records may contain sensitive patient information.

The literature suggests that single-layer moderation is not sufficient for high-risk workflows. A defence-in-depth approach is more appropriate, combining input checks, prompt hardening, retrieval-context filtering, output scanning, and session monitoring. Research on clinical NLP and healthcare AI also emphasises the importance of privacy, auditability, and grounded responses.

However, there is still a gap between conceptual guardrail frameworks and practical clinical QA prototypes. Many systems discuss safety at a high level but do not provide an integrated implementation where input, retrieval, generation, and output controls can be tested together. This project addresses that gap by implementing and evaluating a complete multi-layer guardrail framework around a clinical RAG QA application.

## Project Planning and Management

The project will be completed in stages:

1. Review literature on clinical RAG, LLM guardrails, prompt injection, and healthcare data privacy.
2. Build the clinical QA backend using FastAPI, ChromaDB, and an LLM.
3. Implement and integrate the six-layer guardrail SDK.
4. Build the demo UI and guardrail administration UI.
5. Create benign and adversarial test prompts.
6. Evaluate accuracy, privacy protection, false positives, and performance.
7. Refine the system and write up the findings.

The main technical risks are retrieval errors, overly broad redaction, false positives, and integration complexity between the backend, SDK, and UIs. These risks will be managed through incremental testing, rule tuning, and targeted regression tests.

## References

Greshake, K., Abdelnabi, S., Mishra, S., Endres, C., Holz, T., & Fritz, M. (2023). *Not what you've signed up for: Compromising real-world LLM-integrated applications with indirect prompt injection*. arXiv. https://arxiv.org/abs/2302.12173

Lewis, P., Perez, E., Piktus, A., Petroni, F., Karpukhin, V., Goyal, N., Küttler, H., Lewis, M., Yih, W.-t., Rocktäschel, T., Riedel, S., & Kiela, D. (2020). *Retrieval-augmented generation for knowledge-intensive NLP tasks*. arXiv. https://arxiv.org/abs/2005.11401

National Institute of Standards and Technology. (2023). *Artificial intelligence risk management framework (AI RMF 1.0)* (NIST AI 100-1). U.S. Department of Commerce. https://doi.org/10.6028/NIST.AI.100-1

Open Worldwide Application Security Project. (2025). *OWASP Top 10 for Large Language Model Applications*. https://genai.owasp.org/resource/owasp-top-10-for-llm-applications-2025/

Singhal, K., Azizi, S., Tu, T., Mahdavi, S. S., Wei, J., Chung, H. W., Scales, N., Tanwani, A., Cole-Lewis, H., Pfohl, S., Payne, P., Seneviratne, M., Gamble, P., Kelly, C., Schärli, N., Chowdhery, A., Mansfield, P., Demner-Fushman, D., Agüera y Arcas, B., ... Natarajan, V. (2023). Large language models encode clinical knowledge. *Nature, 620*, 172–180. https://doi.org/10.1038/s41586-023-06291-2

U.S. Department of Health and Human Services. (n.d.). *Guidance regarding methods for de-identification of protected health information in accordance with the HIPAA Privacy Rule*. https://www.hhs.gov/hipaa/for-professionals/special-topics/de-identification/index.html

## AI Usage Declaration

AI tools were used to help improve grammar, structure, and academic tone. The final content was reviewed and adapted to match the implemented clinical QA and guardrail project scope.
