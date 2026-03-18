# netloom v1.7.3

This release moves plugin-specific profile files into plugin-scoped config
directories under `~/.config/netloom/plugins/<plugin>/`.

## Highlights

- plugin-specific `profiles.env` now lives at
  `~/.config/netloom/plugins/<plugin>/profiles.env`
- plugin-specific `credentials.env` now lives at
  `~/.config/netloom/plugins/<plugin>/credentials.env`
- `netloom load <plugin>` now manages the global active plugin marker in
  `~/.config/netloom/config.env`
- `netloom server use <profile>` now updates the active profile inside the
  selected plugin directory

## Example layout

```text
~/.config/netloom/config.env
~/.config/netloom/plugins/clearpass/profiles.env
~/.config/netloom/plugins/clearpass/credentials.env
```

## Recommended setup

```bash
netloom load clearpass
netloom cache update
netloom server use dev
```

Then place your profile files in:

```text
~/.config/netloom/plugins/clearpass/
```
