# Netloom context Prompt

Use this prompt to keep the style consistent 

```text
Context:
- The project root contains `PLANNED_FEATURES.md` with the current priority and status of PLANNED_FEATURES.
- Make sure `PLANNED_FEATURES.md` is updated to reflect the current status of the project when the work changes roadmap/status materially.

Please:
1. Read `PLANNED_FEATURES.md` first. Make a plan to implement the next planned features then wait for user validation to proceed or not.
2. Update tests as needed for the changed behavior.
3. Run targeted `pytest` coverage for the touched area.
4. If Python files changed, run `ruff check` and `ruff format --check` on those files.
5. Update `PLANNED_FEATURES.md` when the work changes roadmap status or completes a planned item.
6. Summarize:
   - successfully implemented changes
   - test/lint results
   - status updates made to `PLANNED_FEATURES.md`
   - any manual follow-up or limitations
7. Do not commit unless I explicitly ask.


Important notes:
- Be careful not to touch unrelated files.
- Prefer `apply_patch` for edits.
- Make sure to update metadata when i ask you to commit changes. If i say "commit vx.x.x" ex commit v1.10.3, please also update the version to the one i specify" 
```
