; =====================================================================
;  plugins/KeepAwake.ahk  —  keep system/display awake module
;  v0.2.0  (ported from standalone KeepAwake v0.1.0)
; =====================================================================
;
;  Uses SetThreadExecutionState. NO synthetic input of any kind:
;  no clicks, no cursor jiggle, no key presses.

class KeepAwakePlugin extends Plugin {
    Name    := "KeepAwake"
    Version := "0.2.0"

    static ES_CONTINUOUS       := 0x80000000
    static ES_SYSTEM_REQUIRED  := 0x00000001
    static ES_DISPLAY_REQUIRED := 0x00000002

    Init() {
        ; Off by default — deliberate opt-in (persisted across runs).
        this.Awake       := this.Cfg.GetBool(this.Name, "Awake", false)
        this.KeepDisplay := this.Cfg.GetBool(this.Name, "KeepDisplay", true)
        this.ApplyState()
    }

    BuildMenu(parentMenu) {
        this.Menu := parentMenu
        parentMenu.Add("Keep awake", ObjBindMethod(this, "ToggleAwake"))
        parentMenu.Add("Keep display on", ObjBindMethod(this, "ToggleDisplay"))
        if this.Awake
            parentMenu.Check("Keep awake")
        if this.KeepDisplay
            parentMenu.Check("Keep display on")
    }

    ToggleAwake(itemName, itemPos, myMenu) {
        this.Awake := !this.Awake
        if this.Awake
            myMenu.Check(itemName)
        else
            myMenu.Uncheck(itemName)
        this.Cfg.SetBool(this.Name, "Awake", this.Awake)
        this.ApplyState()
        this.Notify("Keep awake: " (this.Awake ? "ON" : "OFF"))
    }

    ToggleDisplay(itemName, itemPos, myMenu) {
        this.KeepDisplay := !this.KeepDisplay
        if this.KeepDisplay
            myMenu.Check(itemName)
        else
            myMenu.Uncheck(itemName)
        this.Cfg.SetBool(this.Name, "KeepDisplay", this.KeepDisplay)
        this.ApplyState()          ; re-apply immediately if the hold is active
    }

    ApplyState() {
        if this.Awake {
            flags := KeepAwakePlugin.ES_CONTINUOUS | KeepAwakePlugin.ES_SYSTEM_REQUIRED
            if this.KeepDisplay
                flags |= KeepAwakePlugin.ES_DISPLAY_REQUIRED
        } else {
            flags := KeepAwakePlugin.ES_CONTINUOUS      ; release any previous hold
        }
        return DllCall("kernel32.dll\SetThreadExecutionState", "UInt", flags, "UInt")
    }

    Status() {
        if !this.Awake
            return "off"
        return this.KeepDisplay ? "system + display" : "system only"
    }

    ; Explicitly release the hold. The OS would drop it with the process
    ; anyway, but being explicit keeps disable-without-exit correct.
    Shutdown() {
        DllCall("kernel32.dll\SetThreadExecutionState", "UInt", KeepAwakePlugin.ES_CONTINUOUS, "UInt")
    }
}
