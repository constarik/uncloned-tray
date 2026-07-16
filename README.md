# UnclonedTray

Several small, transparent Windows utilities under **one** tray icon, one
process, one autostart entry — as plain readable AutoHotkey v2 source. No
binary, no installer, nothing hidden.

Part of the [Uncloned Math](https://uncloned.work) toolset.

---

## Modules

| Module | What it does |
|---|---|
| **NumLock** | Force or free Num / Caps / Scroll Lock. Five modes per key: Always On, Always Off, On, Off, Normal. `Always *` suppresses key presses entirely. |
| **KeepAwake** | Keeps the machine (and optionally the display) awake via `SetThreadExecutionState`. **No synthetic input** — no clicks, no mouse jiggle, no fake keystrokes. Off by default. |
| **DownloadsSorter** | Sorts loose files in the *root* of Downloads into category subfolders. Subfolders are never touched. |

Each module gets its own tray submenu with an **Enabled** toggle. Settings
persist in `UnclonedTray.ini` next to the script.

## Why a host instead of separate scripts

Each utility began as a standalone script — and each carried its own copy of
the autostart logic and its own `#SingleInstance`. That turned out to matter:

`#SingleInstance Force` only guards against the *same file path*. A copy in one
folder and a copy in another are, to AutoHotkey, different scripts — they run
side by side. Two file-sorters walking the same directory make every
check-then-act guard meaningless.

One host means one process and one instance, structurally rather than by
convention. It also removes the triplicated autostart code that spawned stray
`.lnk` files in `shell:startup`.

## Not really "plugins"

AutoHotkey has no runtime module loading — `#Include` is resolved at load time
and there is no globbing. "Modules" here means statically included classes
following a registration convention. Adding one is two lines in
`UnclonedTray.ahk`: an `#Include` and an entry in `Modules()`. Dropping a file
into `plugins/` does nothing on its own.

## Install

1. Install [AutoHotkey **v2**](https://www.autohotkey.com/) (v1 will not work).
2. Clone or download this repo.
3. Run `UnclonedTray.ahk`.
4. Tick **Run at startup** in the tray menu if wanted — it creates a single
   shortcut in your user Startup folder. No admin rights required.

## On overwriting

`DownloadsSorter` never overwrites. On a name collision it moves the file to
`name (2).ext`, `name (3).ext`, and so on.

This is enforced with `MoveFileExW` *without* `MOVEFILE_REPLACE_EXISTING`: the
OS itself fails the call if the destination exists, so the existence test and
the move are the same syscall. The older `FileExist()` then `FileMove()` pattern
looks equivalent and is not — the gap between the two is a race window.

It also skips files younger than 15 seconds, partial downloads
(`.crdownload`, `.part`, `.tmp`, `.download`), and hidden/system files. It only
ever moves — nothing is deleted.

If you are replacing a `Move-Item -Force` style sorter, note that `-Force` there
means *overwrite silently*. Files that collide are gone.

## A note on managed / corporate machines

Endpoint protection often treats "keyboard hook + runs at login" as a keylogger
signature, so on locked-down machines these tools may be blocked or quarantined.
That is a policy decision, not a bug. A readable script is far easier to get
approved than a nameless binary — you can hand IT the source.

## License

[MIT](LICENSE) © 2026 Constantin Razinsky / Uncloned Math
