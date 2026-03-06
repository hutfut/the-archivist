# 1. Use Python with FastAPI, React, and LangChain/LangGraph

**Date**: 2026-03-06  
**Status**: Accepted

## Context

This project requires building a simplified NotebookLM: users upload and delete documents, then ask questions in a chat interface where an AI agent answers based on document content. The assessment prompt specifies a preferred stack:

- **React** for the UI
- **Node.js or Python** for server-side components
- **LangChain/LangGraph** for agent orchestration

A mock LLM is acceptable. The application only needs to run locally.

We need to choose between Node.js (TypeScript) and Python for the backend, considering that the frontend (React) and orchestration layer (LangChain/LangGraph) are effectively decided.

## Options considered

1. **TypeScript with Node.js** — Unified language across frontend and backend. Shared type definitions. Single package manager. However, LangChain.js and LangGraph.js are secondary ports of the Python-first libraries: smaller API surface, less documentation, fewer community examples, and updates lag behind the Python SDK. The Node.js ecosystem for document parsing (PDF, DOCX) is less mature.

2. **Python with FastAPI** — LangChain and LangGraph are Python-first: the canonical SDKs with the richest API, best documentation, largest community, and fastest feature cadence. Python has a mature ecosystem for document processing (`pypdf`, `python-docx`, `unstructured`). FastAPI provides automatic OpenAPI/Swagger documentation, Pydantic-based request/response validation, async-native request handling, and built-in dependency injection. The trade-off is maintaining two languages (Python + TypeScript) in one project.

## Decision

**Python with FastAPI** for the backend, **React** for the frontend, **LangChain/LangGraph** (Python SDK) for agent orchestration.

The primary driver is that LangChain/LangGraph — a core requirement of the prompt — is Python-first. Using the canonical SDK means access to the full feature set, the most reliable documentation, and the broadest set of community examples. This directly reduces implementation risk for the agent orchestration layer, which is the most complex part of the system.

FastAPI is a natural complement: Pydantic validation pairs well with structured LangChain I/O, async support handles concurrent chat requests cleanly, and auto-generated OpenAPI docs serve as a living API contract between frontend and backend.

## Consequences

- **Two languages, two dependency systems**: The project uses Python (pip/poetry) for the backend and TypeScript (npm) for the frontend. Developers need familiarity with both ecosystems.
- **No shared types**: API contracts between frontend and backend must be maintained manually or via the OpenAPI spec that FastAPI generates automatically. This is an acceptable trade-off since the API surface is small.
- **Separate processes**: The frontend dev server and backend server run independently. This is true regardless of backend language choice, so it imposes no additional operational cost.
- **Strongest ecosystem fit**: Python gives us the best library support for both document processing and AI agent orchestration, which are the two core capabilities of the application.
