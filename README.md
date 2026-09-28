# Agentic Travel Platform

A multi-agent travel planning platform built with LangGraph and FastMCP, integrating **Snapptrip** as the flight and hotel data source through MCP.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [LangGraph Execution Flow](#langgraph-execution-flow)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Installation](#installation)
  - [Environment Variables](#environment-variables)
  - [Running with Docker Compose](#running-with-docker-compose)
- [Services](#services)
- [API Overview](#api-overview)
- [MCP Tools](#mcp-tools)
- [Long-Term Memory](#long-term-memory)
- [Demo Video](#demo-video)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Overview

This project is a conversational assistant specialized in travel planning for the Iranian market, sourcing live flight and hotel data from **Snapptrip**. Each user has their own account and conversation history, can resume past conversations or start new ones, and the assistant remembers durable preferences across sessions — without the user having to repeat themselves.

Under the hood, a **supervisor agent** classifies each incoming message and decides whether it needs a new flight search, a new hotel search, both, or can be answered directly from context already in the conversation. Specialized agents then call real search tools over MCP, and a **planner agent** produces the final, budget- and preference-aware recommendation.

## Features

- **Multi-agent orchestration** — LangGraph workflow with a supervisor, flight agent, hotel agent, and planner agent
- **Persistent conversations & checkpointing** — Full chat history and LangGraph agent state are persisted to PostgreSQL, allowing conversations to be resumed from their last checkpoint at any time.
- **Parallel search** — Flight and hotel searches run concurrently when both are needed, with results automatically joined before planning
- **Real travel data** — Flight and hotel searches powered by a dedicated FastMCP server integrating with Snapptrip
- **Streaming responses** — Server-Sent Events (SSE) stream real-time status updates (e.g., "Searching flights...") and response tokens
- **Long-term memory** — User preferences are automatically extracted from conversations after each turn and stored as `pgvector` embeddings for semantic retrieval, with near-duplicate detection to prevent redundant entries
- **Fully containerized** — A single command starts the database, migrations, MCP server, backend, and frontend

## LangGraph Execution Flow

<img width="2014" height="1025" alt="graph" src="https://github.com/user-attachments/assets/d18a0046-332b-4d44-9efa-bcde87458d8f" />

## Tech Stack

| Layer | Technology |
|---|---|
| API framework | FastAPI |
| Agent orchestration | LangGraph |
| LLM | `gpt-5-mini` |
| Database | PostgreSQL + async SQLAlchemy |
| Long-term memory | pgvector (semantic search) |
| Conversation persistence | LangGraph's `AsyncPostgresSaver` |
| Migrations | Alembic |
| Search tools | MCP (FastMCP) with Playwright and REST APIs |
| Observability | Langfuse |
| Containerization | Docker Compose |
| CI | GitHub Actions |

## Project Structure

```
agentic-travel-platform/
|
├── .github/workflows/          # CI pipeline
├── agents/                     # LangGraph agent nodes (supervisor, flight, hotel, planner)
├── alembic/                    # Database migrations
├── app/
│   ├── api/                    # FastAPI routers, dependencies
│   ├── core/                   # Security (JWT, password hashing)
│   ├── db/
│   │   ├── models/             # SQLAlchemy models (user, conversation, message, memory)
│   │   ├── base.py
│   │   └── database.py
│   ├── schemas/                # Pydantic request/response schemas
│   └── main.py                 # FastAPI app entrypoint
├── config/                     # Environment-based configuration
├── frontend/                   # Reference web client
├── graph/                      # LangGraph state definition and graph builder
├── mcp_integration/
│   ├── snapptrip/
│   │   ├── flight/             # Playwright-driven flight search client
│   │   └── hotel/              # REST client, response parsing for hotel search
│   ├── tools/                  # MCP tool registrations (search_flights, search_hotels, get_hotel_details)
│   ├── client.py               # MultiServerMCPClient used by the agents
│   └── server.py               # FastMCP server entrypoint
├── memory/                     # Long-term memory service, repository, embeddings
├── tests/                      # pytest suite
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── pyproject.toml
```

## Getting Started

### Installation

Clone the repository:

```bash
git clone https://github.com/aysangh/agentic-travel-platform.git
cd agentic-travel-platform
```

### Environment Variables

Copy the example file and Add your OpenAI API key and other required environment variables to .env.

```bash
cp .env.example .env
```

### Running with Docker Compose

```bash
docker compose up --build
```

Once running:
- **Frontend:** `http://localhost:5173`
- **Backend API:** `http://localhost:8000`

## Services

| Service | Description |
|---|---|
| `postgres` | PostgreSQL 16 with `pgvector`, stores application data, long-term memory embeddings, and LangGraph checkpoints |
| `migrate` | Runs `alembic upgrade head` once and exits |
| `mcp` | FastMCP server exposing `search_flights`, `search_hotels`, and `get_hotel_details` tools |
| `backend` | FastAPI application — authentication, conversations, agent orchestration |
| `frontend` | Reference web client |

## API Overview

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/register` | Create a new account |
| `POST` | `/auth/login` | Log in and receive access/refresh tokens |
| `GET` | `/auth/me` | Get the current authenticated user |
| `GET` | `/conversations` | List the current user's conversations |
| `POST` | `/conversations` | Start a new conversation |
| `GET` | `/conversations/{id}` | Get a conversation and its message history |
| `DELETE` | `/conversations/{id}` | Delete a conversation and its messages |
| `POST` | `/conversations/{id}/messages` | Send a message and stream the assistant's response via SSE |

## MCP Tools

The flight and hotel agents access tools through a dedicated **FastMCP server** (`mcp_integration/server.py`) over **Streamable HTTP**, using `langchain-mcp-adapters`' `MultiServerMCPClient`.

| Tool | Description |
|---|---|
| `search_flights` | Searches round-trip flights between two Iranian cities using Persian city names and Shamsi dates. |
| `search_hotels` | Searches available hotels in an Iranian city for a Shamsi date range, returning hotel details including name, ID, address, star rating, and reviews. |
| `get_hotel_details` | Retrieves available room types for a hotel and Shamsi date range, including pricing, capacity, meal options, and extra-bed pricing. |

Hotel search uses Snapptrip's REST API directly. Flight search uses Playwright browser automation against the Snapptrip website, as Snapptrip does not provide a public flight search API.

## Long-Term Memory

After each conversation turn, an LLM-based extraction step (`memory/long_term.py`) reviews the exchange and identifies **durable** preferences — the kind that remain true across future conversations (e.g. "always flies economy," "travels with a toddler") — while explicitly ignoring one-off, trip-specific details (a single trip's destination or dates). Extracted preferences are:

- Embedded and stored in PostgreSQL via `pgvector`
- Checked against existing memories via cosine similarity, so near-duplicate preferences (similarity ≥ 0.92) aren't stored again
- Retrieved via semantic search against the user's current message, so the most *relevant* preferences — not just the most recent — are surfaced to the supervisor agent on each turn

## Demo Video

[Demo.webm](https://github.com/user-attachments/assets/71c7e271-04d2-4ff5-90c7-8e1d2ec3acf7)

## License

[MIT](LICENSE)

## Acknowledgments

**Flight and hotel data are sourced from [Snapptrip](https://www.snapptrip.com/).**
