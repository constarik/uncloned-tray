# Writing a module for UnclonedTray-Py

Plugin API **1**. A module is one `.py` file in `python\modules\`. The host
finds it at start. A new module stays **off** until the user ticks *Enabled*
in its submenu, so foreign code never runs without the user agreeing.

Start from [`examples/break_reminder.py`](examples/break_reminder.py): copy it
into `python\modules\`, restart the tray, enable it.

## Skeleton

```python
from unclonedtray_api import Plugin

class MyModule(Plugin):
    Name       = "MyModule"      # INI section, unique across all modules
    Version    = "1.0.0"
    ApiVersion = 1               # required, must match the host
    Title      = "My module"     # optional menu caption
    Author     = "you"
    Repo       = "you/my-module" # optional: GitHub repo for update notices
    TagPrefix  = "v"             # its release tags: v1.0.1, ...

    def init(self): ...                    # enabled: start working
    def shutdown(self): ...                # disabled / exit: release what you hold
    def build_menu(self, menu): ...        # fill your submenu
    def status(self): return "..."         # one line for About
```

Files whose name starts with `_` are not loaded (keep helpers there).

## What the host gives you

| Call | Does |
|---|---|
| `self.set_timer(name, ms, fn, once=False)` | calls `fn` every `ms`; the same name re-arms it |
| `self.kill_timer(name)` | stops it; all your timers stop anyway when you are disabled |
| `self.notify(text)` | tray balloon titled with your caption |
| `self.log(text)` | line in `unclonedtray.log`, prefixed with your caption |
| `self.cfg.get_str / get_bool / set_val(self.Name, key, ...)` | settings in `UnclonedTray.ini`, your own section |
| `self.host.add_item(menu, label, fn, checked=False)` | menu item |
| `self.host.add_sep(menu)`, `self.host.new_menu()`, `self.host.add_submenu(menu, label, sub)` | separators and nested menus |
| `RawKeys = (vk, ...)` + `on_raw_key(vkey, flags, hdev)` | told when those keys are touched (Raw Input, not a hook) |

`unclonedtray_api` is the host script itself, so `user32`, `kernel32`, `log`
and the Win32 constants defined there are importable too.

## Rules

- **Everything runs on the tray's single UI thread.** Do not block: no long
  loops, no network calls inside a callback. Use a timer and do a bit at a
  time, or a thread that hands its result back through a timer.
- **The host catches your exceptions.** It logs the traceback with your name.
  After 5 errors in a session it switches you off and tells the user.
  The other modules keep running.
- **Do not touch the tray icon, the window or other modules.**
- **`ApiVersion` must match.** A module written for another API version is
  listed in *About* as not loaded, with the reason.

## Updates

If `Repo` is set and the user has *Updates → Check daily* on, the host checks
that repo's GitHub Releases once a day. A release tagged `TagPrefix + version`
newer than your `Version` shows *Update available* at the top of your
submenu. The host never downloads or replaces files. The user updates by hand.

## Trust

A module is ordinary Python with the user's rights. The host does not sandbox
it. Opt-in and the readable source are the protection, so keep a module
small enough to read.
