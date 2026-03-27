# ClearPass Privilege Mapping Prompt

Use this prompt to continue the remaining ClearPass privilege-mapping work.

```text
Please continue the ClearPass privilege-mapping work in this repository.

Context:
- The project root contains `PLANNED_FEATURES.md` with the current priority and the grouped list of the remaining unmapped retained services.
- The ClearPass privilege rules live in `netloom/plugins/clearpass/privileges.py`.
- The checked-in verification notes live in `netloom/plugins/clearpass/clearpass_privilege_mapping.md`.
- The live discovery runner lives in `netloom/plugins/clearpass/privilege_discovery.py`.
- The current discovery workflow uses:
  - an `admin` profile with full access
  - a `discovery` profile with only the minimum baseline privileges unless I explicitly tell you otherwise
- The goal is to keep verifying service-to-privilege mappings against the real ClearPass server, then promote only cleanly verified mappings into the enforced rule table.

Please:
1. Read `PLANNED_FEATURES.md` first.
2. Review the current verified mappings and the remaining unmapped services.
3. Pick a small, focused next batch of unmapped services to test.
4. Use the existing live discovery workflow:
   - patch the discovery operator profile via the admin profile
   - re-authenticate as the discovery profile
   - probe the real API endpoint
   - restore the original discovery profile privileges afterward
5. Treat a mapping as verified only when:
   - the baseline restricted discovery profile does not already have access
   - the candidate privilege is accepted into the operator profile
   - the effective runtime privileges show the expected key
   - the real endpoint probe succeeds
6. Update or add tests as needed.
7. Run `pytest` on the touched privilege/discovery tests.
8. Run `ruff check` and `ruff format --check` on touched Python files.
9. Summarize:
   - newly verified mappings
   - still unresolved services
   - whether I need to manually change the discovery user privileges before the next round
10. Do not commit unless I explicitly ask.

Important notes:
- Be careful not to touch unrelated files.
- Prefer `apply_patch` for edits.
- Keep `messaging-setup` treated as a likely endpoint-availability issue unless new evidence says otherwise.
- If a service is already accessible with the current discovery baseline, do not claim a minimal privilege mapping without first re-establishing a restrictive baseline that fails.
- When helpful, save candidate batches and live reports in the project root as JSON artifacts so the next round has a clear audit trail.
```
