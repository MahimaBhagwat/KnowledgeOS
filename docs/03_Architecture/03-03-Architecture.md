# KnowledgeOS - System Architecture

# Part 3 — Request-Level Architecture

---

# 20. Request-Level Architecture

This section describes how major user actions are processed inside KnowledgeOS.

Unlike the High-Level and Module-Level Architecture, which describe the overall system organization, the Request-Level Architecture follows individual requests from the user interface through the backend, AI orchestration layer, storage systems, and back to the user.

Each request flow is designed to be modular, secure, explainable, and scalable.

---

# 21. Authentication Flow

## Purpose

Authenticate users securely using Email/Password or Google Sign-In while ensuring complete data isolation.

---

## Flow

```text
User

↓

Frontend

↓

Validate Form

↓

FastAPI

↓

Supabase Authentication

↓

Authentication Successful?

├── No -> Return Error

│      

│  

│

└── Yes

     ↓

Create Session

     ↓

Fetch User Profile

     ↓

Return JWT + User Data

     ↓

Frontend Stores Session

     ↓

Navigate to Home
```

---

## Design Decisions

* Authentication handled entirely by Supabase Auth.
* Backend validates JWT before every protected request.
* Every request includes the authenticated User ID.
* User ID becomes the root identifier for all downstream operations.

---

# 22. Document Upload & Processing Pipeline

## Purpose

Transform uploaded documents into searchable semantic knowledge.

---

## Flow

```text
User Uploads Document

↓

Frontend Validation

↓

FastAPI Upload API

↓

Supabase Storage

↓

Extract Metadata

↓

Document Parser

↓

Chunking

↓

Embedding Generation

↓

Store Embeddings

↓

Store Metadata

↓

Processing Complete

↓

Document Available
```

---

## Detailed Steps

1. Validate file type and size.
2. Upload original file to Supabase Storage.
3. Extract metadata (title, type, pages, size).
4. Parse document into raw text.
5. Split text into semantic chunks.
6. Generate embeddings for each chunk.
7. Store embeddings in ChromaDB.
8. Store metadata in PostgreSQL.
9. Mark document status as **Processed**.

---

## Supported Formats

* PDF
* DOCX
* PPTX
* Markdown
* TXT
* HTML

---

# 23. AI Query Processing Pipeline

## Purpose

Generate trustworthy, personalized, and source-backed responses using Retrieval-Augmented Generation (RAG) and a multi-agent workflow.

---

## Complete Pipeline

```text
                        User Query
                           │
                           ▼
          Authentication & Session Validation
                           │
                           ▼
             Conversation Memory Retrieval
                           │
                           ▼
                  Query Preprocessing
                           │
                           ▼
                    Intent Detection
                           │
         ┌─────────────────┴─────────────────┐
         ▼                                   ▼
   [ Fast Path ]                     [ Complex Path ]
(Greetings/General Chat)             (Deep Knowledge Seek)
         │                                   │
         │                                   ▼
         │                             Planner Agent
         │                                   │
         │                                   ▼
         │                            Query Rewriting
         │                                   │
         │                                   ▼
         │                      Knowledge Source Selection
         │                                   │
         │                                   ▼
         │                            Hybrid Retrieval
         │                                   │
         │                                   ▼
         │                            Context Ranking
         │                                   │
         │                                   ▼
         │                          Context Compression
         │                                   │
         │                                   ▼
         │                          Knowledge Synthesis
         │                                   │
         └─────────────────┬─────────────────┘
                           │
                           ▼
                     Prompt Builder <───────────────┐
                           │                        │
                           ▼                        │
                      LLM Provider                  │
                           │                        │
                           ▼                        │
                     Reviewer Agent                 │
                           │                        │
                           ├───────── FAIL ─────────┘ (Max 2 Retries,
                           │                            passes critique)
                           ▼ PASS
                    Citation Mapping
                           │
                           ▼
                  Response Formatting
                           │
                           ▼
                    Stream Response
                           │
                           ▼
                    Background Tasks
             (Save Conversation, Update Memory, Update Analytics, Logs Metrics)

```

---

## Fast Path Routing

Simple conversational messages such as greetings, acknowledgements, or small talk bypass retrieval and synthesis to minimize latency.

Examples

* Hi
* Hello
* Thanks
* Good Morning

These requests are routed directly to the Prompt Builder and LLM Provider.

---

# 24. Planner–Reviewer Retry Workflow

## Purpose

Improve response quality through iterative validation.

---

## Flow

```text
                    [Planner Agent]
                          │
                          ▼
                    [Prompt Builder]
                          │
                          ▼
                    [LLM Provider]
                          │
                          ▼
                 [ Reviewer Agent ] ──── PASS ─────► Final Response
                          │
                  Validation Failed
                          │
                          ▼
            [ Generate Failure Critique ]
        (e.g., Hallucination, Weak Reasoning, Missing citation, 
            Incomplete answer, Unsafe response)
                          │
                          ▼
           [ Store Critique in State ]
                          │
                          ▼
                  [ Planner Agent ]
            (Updates Retrieval Strategy)
        (e.g., Retrieve more evidence, Search different documents, 
        Remove unsupported claim, Generate more concise answer)
                          │
                          ▼
                  [ Prompt Builder ]
        (Combines Query + Context + Critique)
        (Builds new prompt using : • Original User Query • Retrieved Context 
        • Chat Memory • Planner Instructions • Reviewer's Critique)
                          │
                          ▼
                   [ LLM Provider ]
                          │
                          ▼
                  [ Reviewer Agent ]
                          │
            ┌─────────────┴─────────────┐
            ▼ PASS                      ▼ FAIL
    [ Citation Mapping ]          [ Retry Count++ ]
                                        │
                                        ▼
                            Is Retry Count < 2?
                                ├── YES ──► (Loop back to Planner Agent)
                                │
                                └── NO  ──► [ Fallback Handler ]
                                                  │
                                                  ▼
                                     Return Best verified Response 
                                     + Verification Disclaimer
                                     (Stored and flagged within schema constraints as detailed in 04-07-Database.md Section 21.5)

```

---

## Failure Critique

The Reviewer does not simply reject the response.

Instead, it generates structured feedback describing why validation failed.

Examples

* Unsupported factual claim
* Missing citation
* Weak reasoning
* Incomplete answer
* Unsafe response

The critique becomes part of the workflow state and is injected into the next prompt so the Planner and LLM can produce a more accurate response.

---

# 25. Knowledge Synthesis Pipeline

## Purpose

Combine information from multiple documents into a unified understanding before response generation.

---

## Flow

```text
Retrieved Chunks

↓

Remove Duplicates

↓

Rank by Relevance

↓

Merge Related Concepts

↓

Resolve Conflicts

↓

Build Unified Context

↓

Prompt Builder
```

---

## Design Goals

* Cross-document reasoning
* Reduced redundancy
* Improved prompt quality
* Better factual consistency

---

# 26. Insights Generation Flow

## Purpose

Generate proactive learning insights rather than waiting for user queries.

---

## Flow

```text
User Knowledge Base

↓

Document Metadata

+

Chat History

+

Topic Frequency

↓

Insight Engine

↓

Knowledge Gap Detection

↓

Learning Recommendations

↓

Insights Dashboard
```

---

## Example Outputs

* Frequently studied topics
* Weakly covered concepts
* Suggested revision roadmap
* Most referenced documents
* Learning trends

---

# 27. Document Deletion Flow

## Purpose

Ensure deleted documents are completely removed from the user's knowledge base.

---

## Flow

```text
Delete Request

↓

Authentication

↓

Move to Recently Deleted

↓

Retention Period Check

↓

Permanent Delete

↓

Delete Original File

↓

Delete Metadata

↓

Delete Embeddings

↓

Invalidate Related Context

↓

Deletion Complete
```

---

## Privacy Requirement

After permanent deletion:

* The document must not appear in search results.
* The AI must not retrieve information from it.
* If asked about deleted content, the assistant should respond that the information is no longer available because the document has been removed.

---

# 28. Export & Share Flow

## Purpose

Allow users to download or share AI conversations.

---

## Flow

```text
User Action

↓

Select Format

↓

Generate Export

↓

PDF / Markdown

↓

Download

OR

Generate Share Link

↓

Return Share URL
```

---

## Supported Formats

* PDF
* Markdown

---

# 29. Request-Level Summary

Every major workflow in KnowledgeOS follows a consistent design philosophy:

* Authenticate every request.
* Keep user data isolated.
* Separate orchestration from retrieval.
* Validate AI responses before delivery.
* Stream responses for low perceived latency.
* Execute non-critical updates asynchronously.
* Preserve explainability through citations.
* Ensure deleted knowledge is no longer retrievable.

These request-level flows provide the implementation blueprint for the backend services and AI orchestration while supporting a responsive and trustworthy user experience.
