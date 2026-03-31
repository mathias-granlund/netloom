# netloom v1.10.1

This release makes the ClearPass help and completion experience much more
vendor-like while keeping command visibility aligned with verified privilege
mapping.

## Highlights

- added vendor-style Bash `?` help so the current context can be described
  immediately without pressing `Enter`
- taught the ClearPass catalog parser to read service summaries and canonical
  service names from `/api-docs`, which now surfaces names like
  `certificate-chain`, `certificate-export`, `certificate-sign-request`, and
  `onboard-device`
- unified normal help, cached interactive help, Bash completion, and runtime
  service resolution around the same canonical ClearPass service names
- restored privilege-aware service visibility so user-facing command lists only
  show baseline-accessible or privilege-verified commands even when canonical
  names are available in the full catalog

## Examples

```bash
netloom policyelements ?
netloom certificateauthority certificate-chain --help
netloom certificateauthority certificate-chain get --id=123 --console
```

## Notes

- installable man pages still come from `netloom/data/man/`
- the privilege-aware visible catalog remains the source of truth for
  user-facing command lists
- the richer full catalog is still used behind the scenes to map visible
  services onto their canonical `/api-docs` names when possible
