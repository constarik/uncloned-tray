# =====================================================================
#  break_reminder.py  --  example third-party module for UnclonedTray-Py
#  v1.0.0
#
#  Copy this file into python\modules\ and restart the tray. It shows up
#  switched off; tick Enabled in its submenu to run it.
#
#  Every N minutes a balloon says it is time to stand up. Shows the whole
#  plugin API in ~40 lines: identity, settings in the INI, a timer, a
#  submenu, a status line for About, the log.
# =====================================================================

from unclonedtray_api import Plugin


class BreakReminder(Plugin):
    Name       = "BreakReminder"     # INI section; must be unique
    Version    = "1.0.0"
    Title      = "Break reminder"    # caption in the tray menu
    Author     = "Uncloned Math"
    ApiVersion = 1                   # required: the plugin API this was written for
    Repo       = ""                  # "owner/repo" to get update notices
    TagPrefix  = "v"                 # its release tags: v1.0.1, v1.1.0, ...

    CHOICES = [20, 30, 45, 60]       # minutes

    def init(self):
        self.minutes = int(self.cfg.get_str(self.Name, "Minutes", "45"))
        if self.minutes not in self.CHOICES:
            self.minutes = 45
        self.arm()

    def arm(self):
        self.set_timer("remind", self.minutes * 60_000, self.remind)
        self.log("every %d min" % self.minutes)

    def remind(self):
        self.notify("%d minutes at the screen - stand up for a minute." % self.minutes)

    def choose(self, minutes):
        self.minutes = minutes
        self.cfg.set_val(self.Name, "Minutes", minutes)
        self.arm()                   # same timer name: restarts with the new period

    def build_menu(self, menu):
        for m in self.CHOICES:
            self.host.add_item(menu, "Every %d min" % m,
                               lambda m=m: self.choose(m), checked=(m == self.minutes))

    def status(self):
        return "every %d min" % self.minutes

    # shutdown() not needed: the host stops a module's timers itself
