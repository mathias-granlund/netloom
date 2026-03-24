# netloom v1.9.3

This release adds secure runtime client-secret resolution through OS keychains
without changing the existing ClearPass login flow or token shortcut behavior.
The main focus is letting profiles reference secrets by key instead of keeping
plaintext credentials in profile files.

## Highlights

- added `NETLOOM_CLIENT_SECRET_REF` so plugins can resolve client secrets from
  the OS keychain using the fixed service namespace `netloom/<plugin>`
- kept plaintext `NETLOOM_CLIENT_SECRET` as a supported fallback when keychain
  lookup is unavailable or the referenced entry is missing
- updated `netloom server show`, README guidance, example env files, and the
  ClearPass manpage so keychain-backed and plaintext secret configuration are
  documented clearly
- aligned release metadata and checked-in manpage headers with version `1.9.3`

## Examples

```bash
python -m keyring set netloom/clearpass prod/client-secret

# ~/.config/netloom/plugins/clearpass/credentials/prod.env
NETLOOM_CLIENT_ID=prod-client-id
NETLOOM_CLIENT_SECRET_REF=prod/client-secret

netloom server show
netloom cache update
```

## Notes

- `api_token` and `api_token_file` still take precedence over login-based
  client-secret resolution
- on WSL or other headless Linux environments, `keyring` may require a D-Bus
  session plus `gnome-keyring` or another supported backend before secrets can
  be stored or retrieved
