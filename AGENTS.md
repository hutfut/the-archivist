# Agent Instructions

## Project Context

This is a **take-home technical assessment** for a senior software engineer position. You have 3 days. The assessment prompt is in `PROMPT.md`. Code quality, architecture, and engineering judgment matter more than speed.

## Key Files

- **PROMPT.md** -- The assessment requirements. Read this first and refer back to it throughout.
- **.docs/adr/** -- Write one Architecture Decision Record (ADR) per significant decision; see the README there for format and numbering.
- **.cursor/rules/** -- Project rules that guide code quality, testing, planning, and workflow. These are automatically applied.
- **.cursor/rules/glossary.mdc** -- Definitions for ambiguous terms (e.g. "over-engineer", "unit of work", "system boundaries") used across the rules. Consult this when a term's meaning is unclear.

## Workflow

Follow this order for every unit of work:

1. **Plan** -- Understand what needs to be built. Outline the approach, files involved, and key decisions.
2. **Implement** -- Write clean, well-structured code in small increments.
3. **Test** -- Write tests alongside implementation. Verify they pass.
4. **Review** -- Self-review against the checklist in `.cursor/rules/code-review.mdc`.
5. **Commit** -- Small, atomic commits with conventional commit messages.

## Constraints

- Do not modify `PROMPT.md` -- it contains the original assessment requirements.
- Do not over-engineer. Build what is asked for, well.
- When making a structural or architectural choice, add a new ADR in `.docs/adr/` (one document per decision) before proceeding.
- If something is ambiguous in the prompt, state your assumption explicitly and proceed.
