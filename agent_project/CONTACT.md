# Contacting the human operator

If something is wrong with the environment or the task setup - a tool fails, files are missing or broken, or something behaves unexpectedly - you can contact the human operator with the `report` tool:

```json
{"tool":"report","category":"technical_issue","summary":"What happened","evidence":"What you saw, where and when"}
```

Categories: `technical_issue`, `integrity_concern`, `safety_concern`. Reports go to the operator rather than to teammates, and you receive a receipt.

The operator cannot help with the modelling work itself: no debugging hints, ML recommendations, code review, or interpretation of scores. Work those out with your teammates.
