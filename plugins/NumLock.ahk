; =====================================================================
;  plugins/NumLock.ahk  —  Num/Caps/Scroll Lock manager module
;  v0.2.0  (ported from standalone NumLockManager v0.1.2)
; =====================================================================

class NumLockPlugin extends Plugin {
    Name    := "NumLock"
    Version := "0.2.0"

    static Modes := ["Always On", "Always Off", "On", "Off", "Normal"]
    static Keys  := ["Num", "Caps", "Scroll"]

    static StateValue := Map(
        "Always On",  "AlwaysOn",
        "Always Off", "AlwaysOff",
        "On",         "On",
        "Off",        "Off",
        "Normal",     "" )

    static KeyLabel := Map(
        "Num",    "Num Lock",
        "Caps",   "Caps Lock",
        "Scroll", "Scroll Lock" )

    static Defaults := Map(
        "Num",    "Always On",
        "Caps",   "Always Off",
        "Scroll", "Normal" )

    Init() {
        this.Current  := Map()
        this.KeyMenus := Map()
        for key in NumLockPlugin.Keys {
            mode := this.Get(key, NumLockPlugin.Defaults[key])
            if !NumLockPlugin.StateValue.Has(mode)      ; guard against a hand-edited INI
                mode := NumLockPlugin.Defaults[key]
            this.Current[key] := mode
            this.ApplyState(key, mode)
        }
    }

    ; NOTE: the parameter must NOT be called `menu` — AHK v2 identifiers are
    ; case-insensitive, so `menu` shadows the global `Menu` class and `Menu()`
    ; below would resolve to this parameter instead of the constructor.
    BuildMenu(parentMenu) {
        for key in NumLockPlugin.Keys {
            sub := Menu()
            for mode in NumLockPlugin.Modes
                sub.Add(mode, ObjBindMethod(this, "SelectMode", key, mode))
            this.KeyMenus[key] := sub
            parentMenu.Add(NumLockPlugin.KeyLabel[key], sub)
            this.RefreshChecks(key)
        }
    }

    SelectMode(key, mode, *) {
        this.Current[key] := mode
        this.ApplyState(key, mode)
        this.RefreshChecks(key)
        this.Set(key, mode)                 ; persist choice
    }

    RefreshChecks(key) {
        sub := this.KeyMenus[key]
        for mode in NumLockPlugin.Modes
            sub.Uncheck(mode)
        sub.Check(this.Current[key])        ; radio: exactly one active
    }

    ApplyRaw(key, rawVal) {
        switch key {
            case "Num":    SetNumLockState(rawVal)
            case "Caps":   SetCapsLockState(rawVal)
            case "Scroll": SetScrollLockState(rawVal)
        }
    }

    ApplyState(key, mode) {
        val := NumLockPlugin.StateValue[mode]
        switch val {
            case "AlwaysOn", "AlwaysOff":
                this.ApplyRaw(key, val)      ; force state, key presses suppressed
            case "On", "Off":
                this.ApplyRaw(key, "")       ; release any existing Always lock first
                this.ApplyRaw(key, val)      ; set state, key still toggles
            default:                         ; Normal / ""
                this.ApplyRaw(key, "")       ; release lock, leave current state as-is
        }
    }

    ; Release all locks so the keyboard is left in a normal state on exit.
    Shutdown() {
        for key in NumLockPlugin.Keys
            this.ApplyRaw(key, "")
    }
}
