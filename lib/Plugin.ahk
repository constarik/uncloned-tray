; =====================================================================
;  lib/Plugin.ahk  —  base class for UnclonedTray modules
;  v0.1.0
; =====================================================================
;
;  A module extends Plugin and overrides:
;    Init()            — set up state, timers, hooks. Called once if enabled.
;    BuildMenu(parentMenu) — populate its own tray submenu.
;      NOTE: never name that parameter `menu`. AHK v2 identifiers are
;      case-insensitive, so `menu` shadows the global `Menu` class and any
;      `Menu()` call inside the method resolves to the parameter instead.
;    Shutdown()        — release hooks/holds. Called on exit or disable.
;
;  The host owns the tray, config and autostart. Modules never touch them.

class Plugin {
    Name    := "Unnamed"
    Version := "0.0.0"
    Enabled := true          ; host may override from config

    __New(host) {
        this.Host := host
        this.Cfg  := host.Cfg
    }

    ; --- overridable hooks ---------------------------------------------------
    Init()          => ""
    BuildMenu(parentMenu) => ""
    Shutdown()      => ""

    ; --- helpers available to every module -----------------------------------
    ; Per-module config read/write. Section is the module name, so modules
    ; cannot collide with each other in the INI.
    Get(key, default := "") {
        return this.Cfg.Get(this.Name, key, default)
    }

    Set(key, value) {
        this.Cfg.Set(this.Name, key, value)
    }

    Notify(text) {
        TrayTip(text, this.Name, "Iconi")
    }
}
