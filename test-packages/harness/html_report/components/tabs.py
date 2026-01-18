"""
Tab navigation component builder.

Builds the tab header with buttons for switching between test results,
as well as the container structure for tab content.
"""

from ..models import TabDisplayModel, BuilderConfig
from .base import BaseBuilder


class TabsBuilder(BaseBuilder[list[TabDisplayModel]]):
    """Builds the tabs navigation and container HTML.

    Creates:
    - Tab header with buttons for each test
    - Status icons (checkmark, X, warning) for each tab
    - Tab content containers (content filled separately)
    """

    def build(self, data: list[TabDisplayModel]) -> str:
        """Build tabs header HTML from list of tab display models.

        Args:
            data: List of TabDisplayModel for each test

        Returns:
            Tab header HTML string (just the header buttons)
        """
        self.validate(data)

        buttons_html = []
        for tab in data:
            active_class = " active" if tab.is_active else ""
            status_display = tab.status_display

            button = f'''<button class="tab-button{active_class}" onclick="switchTab('{tab.tab_id}')">
      <span class="tab-icon {status_display.css_class}">{status_display.icon_html}</span>
      <span>{self.escape(tab.tab_label)}</span>
    </button>'''
            buttons_html.append(button)

        return f'''<div class="tabs-header">
    {"".join(buttons_html)}
  </div>'''

    def build_container_start(self) -> str:
        """Build the opening tabs container tag.

        Returns:
            Opening div tag for tabs container
        """
        return '<div class="tabs-container">'

    def build_container_end(self) -> str:
        """Build the closing tabs container tag.

        Returns:
            Closing div tag for tabs container
        """
        return '</div>'

    def build_tab_content_wrapper(
        self,
        tab_id: str,
        content: str,
        is_active: bool = False
    ) -> str:
        """Wrap tab content in its container div.

        Args:
            tab_id: The tab's unique identifier
            content: The HTML content for the tab
            is_active: Whether this tab is initially active

        Returns:
            Tab content wrapped in container div
        """
        active_class = " active" if is_active else ""
        return f'''<div id="{tab_id}" class="tab-content{active_class}">
{content}
</div>'''
