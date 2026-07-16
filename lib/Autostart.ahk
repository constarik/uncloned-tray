; =====================================================================
;  lib/Autostart.ahk  —  single autostart shortcut for the whole toolbelt
;  v0.1.0
; =====================================================================
;
;  Historical note: earlier each standalone script owned its own copy of
;  this logic and its own .lnk. That is how a stray DownloadsSorter.lnk
;  survived in shell:startup and silently launched a SECOND instance
;  alongside a manually started one — two processes sorting one folder,
;  which broke every check-then-act guard in the mover.
;
;  Now there is exactly one shortcut for one host process.

class Autostart {
    static LinkName := "UnclonedTray"

    static LinkPath() {
        return A_Startup "\" Autostart.LinkName ".lnk"
    }

    static IsEnabled() {
        return FileExist(Autostart.LinkPath()) ? true : false
    }

    static Enable() {
        try {
            FileCreateShortcut(A_ScriptFullPath, Autostart.LinkPath(), A_ScriptDir)
            return true
        } catch {
            return false
        }
    }

    static Disable() {
        try {
            FileDelete(Autostart.LinkPath())
            return true
        } catch {
            return false
        }
    }

    static Toggle() {
        if Autostart.IsEnabled() {
            Autostart.Disable()
            return false
        }
        Autostart.Enable()
        return true
    }
}
