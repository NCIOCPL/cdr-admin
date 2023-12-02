#!/usr/bin/env python

"""Close the current session and bring up the home page as guest.
"""

from cdrcgi import Controller


class Control(Controller):
    """Log out and reroute."""

    def run(self):
        """Customized processing."""

        if self.session.name == "guest":
            message = "You are not currently logged in."""
            self.alerts.append(dict(message=message, type="warning"))
        else:
            try:
                self.session.logout()
                self.navigate_to("Admin.py", "guest", logged_out=True)
            except Exception as e:
                self.logger.exception("Failure logging out")
                message = f"Failure logging out: {e}"
                self.alerts.append(dict(message=message, type="error"))


if __name__ == "__main__":
    Control().run()
