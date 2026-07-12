# LangGraph Redis Checkpointer Plan

## Context
The project requires a checkpointer for LangGraph to save ticket state on graph resume and pauses.
The environment will utilize the standard `langgraph-checkpoint-redis` package connected directly to an Upstash Redis TCP instance.

## Approach & Decisions
1. **TCP Connection Support**: Add the provided `REDIS_URL` (rediss://) string to `.env` and `config.py` to allow direct TCP connections to Upstash.
2. **Standard Checkpointer usage**: Since we are using standard TCP sockets, we will natively leverage `langgraph-checkpoint-redis` rather than writing a custom REST implementation.
3. **Serialization**: It will intelligently serialize the strict Pydantic `TicketState` definitions natively through the official library.
4. **Resiliency**: The checkpointer will allow the Dispatcher Agents to securely interrupt and pause while PMs manually interact with or approve maintenance tickets.
