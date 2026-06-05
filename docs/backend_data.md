# DRS v3 Backend Data Documentation

This document serves as the complete technical handoff handbook for the Data Persistence and Schema layers of the Dynamic Translation and Refining System (DRS v3). It details the database folder structures, file schemas, and object serialization rules.

---

## 1. Directory Tree & Data Storage Layout

All data is stored locally in human-readable formats (YAML and JSON). This decouples logic from heavier database dependencies and makes tracking/auditing extremely simple.

```text
drs-v3/
├── memory_store/                # Core persistent databases
│   ├── entities/                # Character registries (YAML)
│   │   └── {project_id}.yaml
│   ├── glossaries/              # Terminology maps (YAML)
│   │   └── {project_id}.yaml
│   ├── styles/                  # Writing style configurations (YAML)
│   │   └── {project_id}.yaml
│   ├── corrections.json         # Global history log of human corrections
│   └── users.json               # Credential database for JWT authentication
├── workspace/                   # Transient state directory
│   └── sessions/                # Active approval gate translation sessions (YAML)
│       └── {session_id}.yaml
└── projects/                    # Output targets for approved documents
    └── {project_id}/
        └── chapters/
            └── {chapter_id}/
                └── approved.md  # Final translated documents
```

---

## 2. File Schemas & Serialization Models

### 1. User Database (`memory_store/users.json`)
- **Format**: JSON list.
- **Fields**:
  - `username` (string): Unique identifier.
  - `hashed_password` (string): Salted PBKDF2 hash.
  - `email` (string, optional): Contact mail.
- **Example**:
  ```json
  [
    {
      "username": "admin",
      "hashed_password": "pbkdf2_sha256$600000$saltvalue$hashvalue...",
      "email": "admin@example.com"
    }
  ]
  ```

### 2. Glossary Registry (`memory_store/glossaries/{project_id}.yaml`)
- **Format**: YAML list of glossary objects.
- **Fields**:
  - `source_term` (string): Key term in the original language.
  - `target_term` (string): Approved translation in target language.
  - `source_lang` (string): ISO code (e.g. `ja`).
  - `target_lang` (string): ISO code (e.g. `vi`).
  - `content_type` (string): `manga` | `fanfic` | `novel` | `general`.
  - `context_note` (string, optional): Contextual helper.
  - `approved_at` (string): ISO timestamp of addition.
  - `approved_by` (string): User identifier (`human` / `ai_seed`).
  - `usage_count` (int): Number of times this glossary term was injected in runs.
- **Example**:
  ```yaml
  - source_term: "先輩"
    target_term: "senpai"
    source_lang: "ja"
    target_lang: "vi"
    content_type: "general"
    context_note: "Keep untranslated for anime community flavor"
    approved_at: "2026-06-04T10:14:02"
    approved_by: "human"
    usage_count: 5
  ```

### 3. Entity Registry (`memory_store/entities/{project_id}.yaml`)
- **Format**: YAML mapping of entity IDs to objects.
- **Fields**:
  - `entity_id` (string): Unique slug key.
  - `canonical_name` (string): Approved translation in target.
  - `source_name` (string): Raw name in source document.
  - `entity_type` (string): `character` | `place` | `title` | `faction` | `term`.
  - `source_lang` (string): Language ISO code.
  - `target_lang` (string): Language ISO code.
  - `pronouns` (string, optional): Preferred target pronouns (e.g., `anh/hắn`, `cô/nàng`).
  - `aliases` (list of strings): Other name variations.
  - `notes` (string, optional): Facts or background history.
- **Example**:
  ```yaml
  luffy:
    entity_id: "luffy"
    canonical_name: "Luffy"
    source_name: "ルフィ"
    entity_type: "character"
    source_lang: "ja"
    target_lang: "vi"
    pronouns: "cậu ấy/hắn"
    aliases:
      - "Mũ Rơm"
    notes: "Thuyền trưởng băng Mũ Rơm, tính cách ngốc nghếch nhưng quả cảm"
  ```

### 4. Style Profile (`memory_store/styles/{project_id}.yaml`)
- **Format**: YAML object containing a list of `StyleRule`s.
- **Fields**:
  - `project_id` (string): Project identifier.
  - `source_lang` (string): Source language ISO.
  - `target_lang` (string): Target language ISO.
  - `content_type` (string): Project genre style.
  - `tone_note` (string): Global tone guideline injected into generator system prompts.
  - `rules` (list of rules):
    - `rule_id` (string): Unique slug identifier.
    - `category` (string): `register` | `honorific` | `sfx` | `dialogue` | `formatting`.
    - `description` (string): Core rule statement.
    - `example_before` (string, optional): Violation example.
    - `example_after` (string, optional): Correct styling example.
- **Example**:
  ```yaml
  project_id: "test-project"
  source_lang: "ja"
  target_lang: "vi"
  content_type: "manga"
  tone_note: "Trẻ trung, hiện đại, hội thoại tự nhiên."
  rules:
    - rule_id: "honorific-handling"
      category: "honorific"
      description: "Dịch các hậu tố kính ngữ tiếng Nhật sang từ xưng hô phù hợp trong tiếng Việt."
      example_before: "Tanaka-san"
      example_after: "Anh Tanaka"
  ```

### 5. Translation Session State (`workspace/sessions/{session_id}.yaml`)
- **Format**: YAML configuration saved during active translation pipelines.
- **Fields**:
  - `session_id` (string): Random UUID tracking active human reviews.
  - `chapter_or_doc` (string): File reference (e.g. `ch001`).
  - `source_text` (string): Original text string.
  - `draft` (string): Proposed translation from AI agents.
  - `corrections` (list of corrections): Proposed correction entities.
- **Example**:
  ```yaml
  session_id: "d974df83-112e-4b77-a87f-3b036573c09f"
  chapter_or_doc: "ch001"
  source_text: "こんにちは先輩"
  draft: "Xin chào senpai"
  corrections: []
  ```

---

## 3. Data Integration & Auto-Promotion Code Logic

When a user approves a translation and sends proposed corrections via the API, the system runs an **Auto-Promotion Flow**:

```text
User Submission (ApproveRequest)
 └── Extract corrections
      └── Validate type (glossary/entity)
           └── Deduplicate & Merge
                └── Write back to:
                     - memory_store/glossaries/{project_id}.yaml
                     - memory_store/entities/{project_id}.yaml
```

The deduplication logic protects data integrity by merging identical term mappings instead of creating redundant rows, updating usage metadata on matches.
