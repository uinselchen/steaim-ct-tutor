# Computational Thinking Analysis

## Goal

Add evidence-based Computational Thinking (CT) feedback to the tutor's first
lesson-plan analysis. The feature must identify CT only when learners perform
the corresponding cognitive practice, connect each finding to a concrete
lesson activity, and suggest small activity-level refinements where useful.

## Scope

The feature covers six CT dimensions:

- Decomposition
- Pattern recognition / generalisation
- Abstraction
- Algorithmic thinking
- Testing / debugging / evaluation
- Data / representation

It adds feedback to Step 2 only. It does not automatically modify the lesson
plan or add a new refinement topic in Step 3.

## Analysis Contract

The existing analysis request remains a single Mistral request. The analysis
system prompt will require a `computational_thinking` array with exactly one
entry for each CT dimension. Each entry contains:

```json
{
  "practice": "Decomposition",
  "status": "Present | Opportunity | Not identified",
  "activity": "Activity 2",
  "evidence": "A concise description of the learner action or the absence of evidence.",
  "limitation": "A specific limitation when the practice is weakly represented.",
  "refinement": "A concrete modification that fits the existing lesson goals, or an empty string."
}
```

The prompt must explicitly prohibit classification based only on keywords,
lesson topic, technology use, programming terminology, or teacher activity.
`Present` requires clear learner evidence. `Opportunity` is reserved for an
existing activity that can support the practice through a small, goal-aligned
modification. `Not identified` means that the lesson plan provides no
sufficient evidence.

## Backend Behaviour

- Preserve the CT block returned by the existing analysis endpoint.
- Normalize missing, malformed, or unknown CT values safely before returning
  the analysis to the browser.
- Ensure all six dimensions are represented, using `Not identified` defaults
  for missing entries.
- Do not log API keys or full secrets while handling the analysis.

## Step 2 UI

Add a dedicated `Computational Thinking` feedback box below the existing
analysis categories and before the upload/next-step controls.

The collapsed overview is a compact table with one row per CT practice and
the columns:

- CT practice
- Status
- Associated activity

Each row can be expanded to show:

- Evidence
- Limitation, when present
- Possible refinement, when present

Status presentation is neutral and descriptive:

- `Present`: green accent
- `Opportunity`: yellow accent
- `Not identified`: muted neutral accent

The box must also render when all practices are `Not identified`, making the
absence of evidence explicit instead of hiding it.

## Testing

Add regression tests for:

- Complete CT response normalization.
- Missing and unknown CT statuses defaulting safely.
- Preservation of activity-level evidence and refinements.
- Existing analysis and configuration tests continuing to pass.

The final verification includes the full test suite and the existing Windows
launcher check.
