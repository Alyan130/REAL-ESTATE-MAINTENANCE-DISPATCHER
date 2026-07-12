## Architecture: langgraph-redis-checkpointer

```mermaid
graph TD
    A[Ticket State Graph (Agent)] -->|Requires persistence| B[RedisSaver]
    B -->|Uses redis-py SDK| C[TCP Socket / SSL Connection]
    C --> D[(Upstash Redis Database)]
    D -->|Loads checkpoint matching thread_id| C
    C -->|Returns binary/JSON checkpoint| B
    B -->|Deserializes state| A
    E[Config / Settings] -.->|Provides REDIS_URL| B
```
