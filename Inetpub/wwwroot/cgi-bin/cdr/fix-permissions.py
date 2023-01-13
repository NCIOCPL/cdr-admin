#!/usr/bin/env python

"""Undo havoc wreaked by the Windows file permissions system.
"""

from functools import cached_property
from pathlib import Path
from cdr import run_command
from cdrcgi import Controller


class Control(Controller):

    LOGNAME = "fix-permissions"

    def run(self):
        """Fix the permissions on the specified files/directories."""

        path = self.fields.getvalue("path")
        if not path:
            path = self.session.tier.logdir
        path = Path(path).resolve()
        command = f"{self.fix_permissions} {path}"
        self.logger.info("fixing permissions for %s", path)
        try:
            result = run_command(command, merge_output=True)
            self.send_page(result.stdout, text_type="plain")
        except Exception as e:
            self.logger.exception(command)
            self.send_page(f"{command}: {e}")

    @cached_property
    def fix_permissions(self):
        """Location of the script we run."""
        return Path(self.session.tier.basedir, "bin", "fix-permissions.cmd")


if __name__ == "__main__":
    Control().run()
