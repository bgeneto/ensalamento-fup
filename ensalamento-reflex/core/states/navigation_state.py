"""Navigation state for single-page application routing."""

from typing import Dict, List

import reflex as rx


class NavigationState(rx.State):
    """Global navigation state for SPA routing.

    Manages page navigation, breadcrumbs, and navigation history
    for the single-page application architecture.
    """

    # Current page
    current_page: str = "dashboard"

    # Breadcrumb navigation
    breadcrumbs: List[Dict[str, str]] = []

    @rx.var
    def current_page_title(self) -> str:
        """Computed page title based on current page."""
        titles = {
            "dashboard": "Dashboard",
            "allocation": "Ensalamento",
            "inventory": "Inventário",
            "professors": "Professores",
            "rules": "Regras",
            "demand": "Demanda",
            "visualization": "Visualização",
            "reservations": "Reservas",
            "settings": "Configurações",
            "manual_allocation": "Alocação Manual",
            "reports": "Relatórios",
        }
        return titles.get(self.current_page, "Página Desconhecida")

    @rx.var
    def current_page_icon(self) -> str:
        """Computed page icon based on current page."""
        icons = {
            "dashboard": "home",
            "allocation": "check_circle",
            "inventory": "building",
            "professors": "person",
            "rules": "list",
            "demand": "search",
            "visualization": "bar_chart",
            "reservations": "calendar_today",
            "settings": "settings",
            "manual_allocation": "edit",
            "reports": "description",
        }
        return icons.get(self.current_page, "circle")

    @rx.var
    def can_go_back(self) -> bool:
        """Check if back navigation is available."""
        return len(self.breadcrumbs) > 1

    @rx.var
    def breadcrumb_items(self) -> List[Dict[str, str]]:
        """Computed breadcrumb items for navigation display."""
        # Always include Home as first item
        items = [{"label": "Home", "page": "dashboard", "icon": "home"}]

        # Add current page if not dashboard
        if self.current_page != "dashboard":
            items.append(
                {
                    "label": self.current_page_title,
                    "page": self.current_page,
                    "icon": self.current_page_icon,
                }
            )

        return items

    def navigate_to(self, page: str):
        """Navigate to a page and update breadcrumbs.

        Args:
            page: Target page key
        """
        if page != self.current_page:
            # Add current page to breadcrumbs if not already there
            current_crumb = {
                "label": self.current_page_title,
                "page": self.current_page,
                "icon": self.current_page_icon,
            }

            # Avoid duplicates in breadcrumbs
            if (
                not self.breadcrumbs
                or self.breadcrumbs[-1]["page"] != self.current_page
            ):
                self.breadcrumbs.append(current_crumb)

            # Update current page
            self.current_page = page

            # Update breadcrumbs for new page
            self._update_breadcrumbs_for_page(page)

    def go_back(self):
        """Navigate to previous page in breadcrumb history."""
        if self.can_go_back:
            # Remove current page from breadcrumbs
            self.breadcrumbs.pop()

            # Navigate to last item in breadcrumbs
            last_crumb = self.breadcrumbs[-1]
            self.current_page = last_crumb["page"]

            # Update breadcrumbs for the target page
            self._update_breadcrumbs_for_page(self.current_page)

    def go_home(self):
        """Navigate to dashboard/home page and reset breadcrumbs."""
        self.current_page = "dashboard"
        self.breadcrumbs = []

    def _update_breadcrumbs_for_page(self, page: str):
        """Update breadcrumb trail for specific page.

        Args:
            page: Page key to update breadcrumbs for
        """
        if page == "dashboard":
            self.breadcrumbs = []
        else:
            # Keep breadcrumbs up to current page
            updated_crumbs = []

            # Always include home
            updated_crumbs.append(
                {"label": "Home", "page": "dashboard", "icon": "home"}
            )

            # Add current page
            updated_crumbs.append(
                {
                    "label": self.current_page_title,
                    "page": page,
                    "icon": self.current_page_icon,
                }
            )

            self.breadcrumbs = updated_crumbs

    # Page navigation helpers
    def go_to_dashboard(self):
        """Navigate to dashboard."""
        self.navigate_to("dashboard")

    def go_to_allocation(self):
        """Navigate to allocation page."""
        self.navigate_to("allocation")

    def go_to_inventory(self):
        """Navigate to inventory page."""
        self.navigate_to("inventory")

    def go_to_professors(self):
        """Navigate to professors page."""
        self.navigate_to("professors")

    def go_to_rules(self):
        """Navigate to rules page."""
        self.navigate_to("rules")

    def go_to_demand(self):
        """Navigate to demand page."""
        self.navigate_to("demand")

    def go_to_visualization(self):
        """Navigate to visualization page."""
        self.navigate_to("visualization")

    def go_to_reservations(self):
        """Navigate to reservations page."""
        self.navigate_to("reservations")

    def go_to_settings(self):
        """Navigate to settings page."""
        self.navigate_to("settings")

    def go_to_manual_allocation(self):
        """Navigate to manual allocation page."""
        self.navigate_to("manual_allocation")

    def go_to_reports(self):
        """Navigate to reports page."""
        self.navigate_to("reports")

    # Utility methods
    def is_current_page(self, page: str) -> bool:
        """Check if given page is the current page.

        Args:
            page: Page key to check

        Returns:
            True if page is current page
        """
        return self.current_page == page

    def get_page_url(self, page: str) -> str:
        """Get URL path for a page.

        Args:
            page: Page key

        Returns:
            URL path for the page
        """
        url_map = {
            "dashboard": "/",
            "allocation": "/allocation",
            "inventory": "/inventory",
            "professors": "/professors",
            "rules": "/rules",
            "demand": "/demand",
            "visualization": "/visualization",
            "reservations": "/reservations",
            "settings": "/settings",
            "manual_allocation": "/manual-allocation",
            "reports": "/reports",
        }
        return url_map.get(page, "/")

    # Menu configuration
    @rx.var
    def main_menu_items(self) -> List[Dict[str, str]]:
        """Main navigation menu items."""
        return [
            {"key": "dashboard", "label": "Dashboard", "icon": "home"},
            {"key": "allocation", "label": "Ensalamento", "icon": "check_circle"},
            {"key": "inventory", "label": "Inventário", "icon": "building"},
        ]

    @rx.var
    def management_menu_items(self) -> List[Dict[str, str]]:
        """Management navigation menu items."""
        return [
            {"key": "professors", "label": "Professores", "icon": "person"},
            {"key": "rules", "label": "Regras", "icon": "list"},
            {"key": "demand", "label": "Demanda", "icon": "search"},
        ]

    @rx.var
    def tools_menu_items(self) -> List[Dict[str, str]]:
        """Tools navigation menu items."""
        return [
            {"key": "visualization", "label": "Visualização", "icon": "bar_chart"},
            {"key": "reservations", "label": "Reservas", "icon": "calendar_today"},
            {"key": "settings", "label": "Configurações", "icon": "settings"},
        ]
