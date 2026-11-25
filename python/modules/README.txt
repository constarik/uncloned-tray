UnclonedTray-Py modules folder
==============================

Every .py file here is a module. The tray finds it at start.

How to add a module
-------------------
1. Put the module's .py file into this folder.
   (Files whose name starts with "_" are not loaded - keep helpers there.)
2. Restart the tray: tray menu -> Exit, then start it again.
3. A new module is OFF until you turn it on:
   tray menu -> Modules -> tick the module.
   Foreign code never runs without you agreeing.

A file that could not be loaded is shown greyed out in the Modules
menu with the reason; details are in unclonedtray.log.

Writing your own
----------------
Start from break_reminder.py (in this folder): copy it under a new
file name, change Name / Title / Version, and edit. The full guide is
..\MODULES.md (tray menu -> Modules -> How to add a module).

A module is ordinary Python with your rights - the tray does not
sandbox it. Only add modules whose source you have read.
