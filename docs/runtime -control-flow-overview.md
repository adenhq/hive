# Runtime Control Flow Overview (High-Level)

This document provides a quick, contributor-friendly overview of how a goal/request flows through Hive at runtime — from initialization to node execution, evaluation, and choosing the next step.

## TL;DR Flow

```mermaid
flowchart TD
  A[Goal / User Request] --> B[Runner / Entry Point]
  B --> C[GraphExecutor]
  C --> D[Select Next Node]
  D --> E[Execute Node Logic]
  E --> F{Tool Call Needed?}
  F -- Yes --> G[Tool Execution]
  G --> H[Update Context / State]
  F -- No --> H[Update Context / State]
  H --> I{Evaluation / Guardrails?}
  I -- Yes --> J[Evaluate Output / Decide Next Step]
  I -- No --> K[Traverse Edge / Continue]
  J --> K[Traverse Edge / Continue]
  K --> D[Select Next Node]
  K --> L[Stop Condition Met?]
  L -- Yes --> M[Finalize Response]
  L -- No --> D
