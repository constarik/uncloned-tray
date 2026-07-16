; =====================================================================
;  plugins/DownloadsSorter.ahk  —  sorts loose files in Downloads root
;  v0.2.0  (ported from standalone DownloadsSorter v0.1.1)
; =====================================================================
;
;  Safety guards:
;    - only LOOSE files in the ROOT of Downloads; subfolders never touched;
;    - incomplete downloads and files younger than FRESH_SECONDS skipped;
;    - hidden/system files left alone;
;    - name collisions -> " (2)", " (3)"...; NEVER overwrites;
;    - move only, nothing is ever deleted.
;
;  v0.2.0 fix — ATOMIC MOVE:
;    v0.1.1 did FileExist(dest) then FileMove(src, dest, false). That is a
;    check-then-act (TOCTOU) race: the gap between the two is not atomic.
;    With two instances running (a stale shell:startup .lnk plus a manual
;    launch) both computed a "free" destination and one clobbered the other's
;    file. FileMove with Overwrite=false is NOT reliably atomic across
;    processes either, so we now use MoveFileExW WITHOUT MOVEFILE_REPLACE_EXISTING:
;    the OS itself fails the call if the destination exists. No gap to race in.
;    Under the host there is one process by construction, but the mover is
;    made correct on its own terms regardless.

class DownloadsSorterPlugin extends Plugin {
    Name    := "DownloadsSorter"
    Version := "0.2.0"

    static AUTO_INTERVAL := 30000     ; ms between auto scans
    static FRESH_SECONDS := 15        ; do not touch files younger than N seconds
    static OTHER_FOLDER  := "Other"
    static MAX_COLLISION := 999       ; give up rather than spin forever

    static Categories := Map(
        "Images",        ["jpg","jpeg","png","gif","bmp","webp","svg","tif","tiff","ico","heic"],
        "Documents",     ["pdf","doc","docx","txt","rtf","odt","md","tex"],
        "Spreadsheets",  ["xls","xlsx","csv","ods"],
        "Presentations", ["ppt","pptx","odp"],
        "Archives",      ["zip","rar","7z","tar","gz","xz","iso"],
        "Video",         ["mp4","mkv","avi","mov","webm","wmv","m4v"],
        "Audio",         ["mp3","wav","flac","aac","ogg","m4a"],
        "Installers",    ["exe","msi","msix"],
        "Code",          ["py","js","ts","java","c","cpp","h","cs","ahk","json","xml","html","css","sh","bat","ps1","jar"] )

    static SkipExt := Map("crdownload", 1, "part", 1, "tmp", 1, "download", 1)

    Init() {
        ; extension -> category (inverted once)
        this.ExtCat := Map()
        for cat, exts in DownloadsSorterPlugin.Categories
            for e in exts
                this.ExtCat[e] := cat

        this.Auto := this.Cfg.GetBool(this.Name, "Auto", true)   ; auto-watch ON by default
        this.Timer := ObjBindMethod(this, "Tick")
        if this.Auto
            SetTimer(this.Timer, DownloadsSorterPlugin.AUTO_INTERVAL)
    }

    BuildMenu(parentMenu) {
        parentMenu.Add("Sort now", (*) => this.RunSort(true))
        parentMenu.Add("Auto-watch", ObjBindMethod(this, "ToggleAuto"))
        parentMenu.Add()
        parentMenu.Add("Show folder", (*) => Run(this.DownloadsPath()))
        if this.Auto
            parentMenu.Check("Auto-watch")
    }

    ToggleAuto(itemName, itemPos, myMenu) {
        this.Auto := !this.Auto
        if this.Auto
            myMenu.Check(itemName)
        else
            myMenu.Uncheck(itemName)
        this.Cfg.SetBool(this.Name, "Auto", this.Auto)
        SetTimer(this.Timer, this.Auto ? DownloadsSorterPlugin.AUTO_INTERVAL : 0)
        this.Notify("Auto-watch: " (this.Auto ? "ON" : "OFF"))
    }

    Tick() {
        this.RunSort(false)
    }

    RunSort(manual) {
        n := this.SortOnce()
        if (manual || n > 0)
            this.Notify("Files moved: " n)
    }

    Shutdown() {
        SetTimer(this.Timer, 0)
    }

    Status() {
        return this.Auto ? "auto" : "manual"
    }

    ; Sorts the Downloads root once. Returns the number of files moved.
    SortOnce() {
        dl := this.DownloadsPath()
        if !DirExist(dl)
            return 0

        ; collect first, then move (do not mutate during enumeration)
        files := []
        Loop Files, dl "\*.*", "F"          ; F = files only, no R = root only
            files.Push({ name: A_LoopFileName, path: A_LoopFileFullPath })

        moved := 0
        for f in files {
            if (f.path = A_ScriptFullPath)          ; never touch the host script
                continue

            attrib := FileGetAttrib(f.path)
            if (InStr(attrib, "H") || InStr(attrib, "S"))    ; hidden/system
                continue

            SplitPath(f.name, , , &ext)
            ext := StrLower(ext)

            if DownloadsSorterPlugin.SkipExt.Has(ext)        ; incomplete download
                continue

            mtime := FileGetTime(f.path, "M")                ; still being written?
            if (DateDiff(A_Now, mtime, "Seconds") < DownloadsSorterPlugin.FRESH_SECONDS)
                continue

            cat := this.ExtCat.Has(ext) ? this.ExtCat[ext] : DownloadsSorterPlugin.OTHER_FOLDER
            if this.MoveFileAtomic(f.path, dl "\" cat, f.name)
                moved += 1
        }
        return moved
    }

    ; Moves a file into targetDir, never overwriting.
    ;
    ; Uses MoveFileExW WITHOUT the MOVEFILE_REPLACE_EXISTING flag: if the
    ; destination already exists, the OS refuses the call (ERROR_ALREADY_EXISTS
    ; / ERROR_FILE_EXISTS) and nothing is touched. We then try the next
    ; candidate name. There is no check-then-act window for anyone to race:
    ; the existence test and the move are the same syscall.
    MoveFileAtomic(srcPath, targetDir, fileName) {
        if !DirExist(targetDir) {
            try DirCreate(targetDir)
            catch
                return false
        }

        SplitPath(fileName, , , &ext, &nameNoExt)

        n := 1
        loop DownloadsSorterPlugin.MAX_COLLISION {
            dest := (n = 1)
                ? targetDir "\" fileName
                : (ext != ""
                    ? targetDir "\" nameNoExt " (" n ")." ext
                    : targetDir "\" nameNoExt " (" n ")")

            ; MoveFileExW(src, dst, flags); flags = 0 -> fail if dst exists.
            if DllCall("kernel32.dll\MoveFileExW", "WStr", srcPath, "WStr", dest, "UInt", 0)
                return true

            err := A_LastError
            ; 80 = ERROR_FILE_EXISTS, 183 = ERROR_ALREADY_EXISTS -> try next name
            if (err != 80 && err != 183)
                return false      ; locked/busy/permission — leave it for next scan

            n += 1
        }
        return false              ; absurd number of collisions — give up safely
    }

    ; --- Downloads path detection (registry + env expansion, OneDrive-aware) --
    DownloadsPath() {
        guid := "{374DE290-123F-4565-9164-39C4925E467B}"
        for hive in ["User Shell Folders", "Shell Folders"] {
            try {
                raw := RegRead("HKCU\Software\Microsoft\Windows\CurrentVersion\Explorer\" hive, guid)
                if (raw != "") {
                    path := this.ExpandEnv(raw)
                    if DirExist(path)
                        return path
                }
            }
        }
        return EnvGet("USERPROFILE") "\Downloads"       ; fallback
    }

    ExpandEnv(str) {
        if !InStr(str, "%")
            return str
        try {
            size := DllCall("ExpandEnvironmentStringsW", "WStr", str, "Ptr", 0, "UInt", 0, "UInt")
            if (size > 0) {
                buf := Buffer(size * 2)
                DllCall("ExpandEnvironmentStringsW", "WStr", str, "Ptr", buf, "UInt", size, "UInt")
                return StrGet(buf, "UTF-16")
            }
        }
        return StrReplace(str, "%USERPROFILE%", EnvGet("USERPROFILE"))
    }
}
