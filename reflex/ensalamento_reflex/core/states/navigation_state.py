"""
Navigation State - Reflex Implementation
Follows state management patterns from docs/Reflex_Architecture_Document.md
"""

import reflex as rx


class NavigationState(rx.State):
    """Global navigation state for SPA routing"""

    current_page: str = "dashboard"
    breadcrumbs: list[dict] = []

    @rx.var
    def current_page_title(self) -> str:
        """Computed page title based on current page"""
        titles = {
            "dashboard": "Dashboard",
            "inventory": "Room Management",
            "allocation": "Room Allocation",
            "allocation-autonomous": "Autonomous Allocation",
            "allocation-manual": "Manual Allocation",
            "professors": "Professor Management",
            "reservations": "Reservations",
            "settings": "Settings",
            "login": "Login",
        }
        return titles.get(self.current_page, "Unknown")

    @rx.var
    def can_go_back(self) -> bool:
        """Check if back navigation is available"""
        return len(self.breadcrumbs) > 1

    def navigate_to(self, page: str):
        """
        Navigate to a page and update breadcrumbs

        Follows defensive mutation pattern
        """
        if page != self.current_page:
            # Add current to breadcrumbs if not already there
            current_crumb = {
                "label": self.current_page_title,
                "page": self.current_page,
            }
            if (
                not self.breadcrumbs
                or self.breadcrumbs[-1]["page"] != self.current_page
            ):
                self.breadcrumbs.append(current_crumb)

            self.current_page = page

            # Update breadcrumbs to new page
            self.breadcrumbs = [
                {"label": "Home", "page": "dashboard"},
                {"label": self.current_page_title, "page": page},
            ]

            # Apply defensive mutation to breadcrumbs
            self.breadcrumbs = list(self.breadcrumbs)

    def go_back(self):
        """
        Navigate to previous page in breadcrumbs

        Returns appropriate redirect event
        """
        if self.can_go_back:
            self.breadcrumbs.pop()
            last_crumb = self.breadcrumbs[-1]
            self.current_page = last_crumb["page"]
            return rx.redirect(f"/{last_crumb['page']}")

        # Fallback to dashboard if no back available
        return rx.redirect("/dashboard")
