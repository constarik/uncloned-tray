; =====================================================================
;  lib/Config.ahk  —  INI wrapper for UnclonedTray
;  v0.1.0
; =====================================================================
;
;  One INI next to the host. Section per module, so modules cannot
;  collide. Values are plain strings; callers coerce as needed.

class Config {
    __New(path) {
        this.Path := path
    }

    Get(section, key, default := "") {
        return IniRead(this.Path, section, key, default)
    }

    Set(section, key, value) {
        try IniWrite(value, this.Path, section, key)
    }

    ; Convenience for on/off flags stored as 1/0.
    GetBool(section, key, default := false) {
        v := this.Get(section, key, default ? "1" : "0")
        return (v = "1" || v = "true")
    }

    SetBool(section, key, value) {
        this.Set(section, key, value ? "1" : "0")
    }
}
