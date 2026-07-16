#Requires AutoHotkey v2.0
#SingleInstance Force

; =====================================================================
;  UnclonedTray  —  several small transparent utilities under one tray icon
;  AutoHotkey v2
;  v0.1.0
;
;  Part of the Uncloned Math toolset — https://uncloned.work
;
;  Modules are statically included below and registered in Modules().
;  Note on terminology: AutoHotkey has no runtime plugin loading — there is
;  no #Include globbing — so "modules" here means statically included classes
;  with a registration convention, NOT hot-pluggable drop-in files.
;
;  Why a host at all:
;    Each utility used to be a standalone script with its own copy of the
;    autostart logic and its own #SingleInstance. #SingleInstance Force only
;    guards against the SAME file path, so a copy in Downloads and a copy in
;    ClaudeLab happily ran side by side — two processes sorting one folder,
;    which is exactly how the mover's guard got raced and a file was clobbered.
;    One host = one process = one instance, structurally.
; =====================================================================

#Include lib\Config.ahk
#Include lib\Autostart.ahk
#Include lib\Plugin.ahk
#Include plugins\NumLock.ahk
#Include plugins\KeepAwake.ahk
#Include plugins\DownloadsSorter.ahk

APP_NAME := "UnclonedTray"
VERSION  := "0.1.0"

host := TrayHost(APP_NAME, VERSION)
host.Start()

Persistent()      ; keep resident (a tray menu alone does not hold the script)

OnExit(ExitHandler)

TrayTip(APP_NAME " v" VERSION " started`n" host.Summary(), APP_NAME, "Iconi")

; --- auto-execute section ends here. No Return: class definitions below are
; --- statements, and a Return would make them unreachable at load time.

ExitHandler(*) {
    global host
    host.Shutdown()
    return 0
}

; ============================== host =========================================

class TrayHost {
    __New(name, version) {
        this.AppName := name
        this.Version := version
        this.Cfg     := Config(A_ScriptDir "\" name ".ini")
        this.Plugins := []
    }

    ; Module registry. Adding a module = one line here + one #Include above.
    Modules() {
        return [NumLockPlugin, KeepAwakePlugin, DownloadsSorterPlugin]
    }

    Start() {
        for cls in this.Modules() {
            p := cls(this)
            p.Enabled := this.Cfg.GetBool(p.Name, "Enabled", true)
            this.Plugins.Push(p)
            if p.Enabled {
                try p.Init()
                catch as e
                    this.ModuleError(p, e)
            }
        }
        this.BuildTray()
        A_IconTip := this.AppName " v" this.Version
    }

    ModuleError(p, e) {
        p.Enabled := false
        MsgBox("Module '" p.Name "' failed to start and was disabled:`n`n"
             . e.Message, this.AppName, "Icon!")
    }

    BuildTray() {
        A_TrayMenu.Delete()
        for p in this.Plugins {
            sub := Menu()
            if p.Enabled {
                ; A bare `try` without `catch` swallows the error silently and
                ; leaves an empty submenu with no clue why — never do that.
                try {
                    p.BuildMenu(sub)
                } catch as e {
                    this.ModuleError(p, e)
                }
                sub.Add()
            }
            sub.Add("Enabled", ObjBindMethod(this, "ToggleModule", p))
            if p.Enabled
                sub.Check("Enabled")
            A_TrayMenu.Add(p.Name, sub)
        }
        A_TrayMenu.Add()
        A_TrayMenu.Add("Run at startup", ObjBindMethod(this, "ToggleAutostart"))
        if Autostart.IsEnabled()
            A_TrayMenu.Check("Run at startup")
        A_TrayMenu.Add()
        A_TrayMenu.Add("About", ObjBindMethod(this, "ShowAbout"))
        A_TrayMenu.Add("Exit", (*) => ExitApp())
    }

    ; Enabling/disabling a module rebuilds the tray, so its submenu appears
    ; or collapses immediately.
    ToggleModule(p, *) {
        if p.Enabled {
            try p.Shutdown()
            p.Enabled := false
        } else {
            p.Enabled := true
            try p.Init()
            catch as e {
                this.ModuleError(p, e)
                this.BuildTray()
                return
            }
        }
        this.Cfg.SetBool(p.Name, "Enabled", p.Enabled)
        this.BuildTray()
        TrayTip(p.Name ": " (p.Enabled ? "enabled" : "disabled"), this.AppName, "Iconi")
    }

    ToggleAutostart(itemName, itemPos, myMenu) {
        on := Autostart.Toggle()
        on ? myMenu.Check(itemName) : myMenu.Uncheck(itemName)
    }

    Summary() {
        parts := []
        for p in this.Plugins
            if p.Enabled
                parts.Push(p.Name)
        return parts.Length ? "Active: " . this.Join(parts, ", ") : "No modules enabled"
    }

    Join(arr, sep) {
        s := ""
        for i, v in arr
            s .= (i > 1 ? sep : "") v
        return s
    }

    ShowAbout(*) {
        msg := this.AppName " v" this.Version "`n`n"
        msg .= "Small, transparent utilities under one tray icon.`n"
        msg .= "One process, one instance, one autostart entry.`n`n"
        msg .= "Modules:`n"
        for p in this.Plugins {
            line := "  " p.Name "  v" p.Version "  — " (p.Enabled ? "enabled" : "disabled")
            if (p.Enabled && p.HasMethod("Status"))
                try line .= " (" p.Status() ")"
            msg .= line "`n"
        }
        msg .= "`nConfig: " this.Cfg.Path "`n`n"
        msg .= "AutoHotkey v2  ·  uncloned.work"
        MsgBox(msg, this.AppName, "Iconi")
    }

    ; Called on exit: every enabled module releases its hooks/holds.
    Shutdown() {
        for p in this.Plugins
            if p.Enabled
                try p.Shutdown()
    }
}
