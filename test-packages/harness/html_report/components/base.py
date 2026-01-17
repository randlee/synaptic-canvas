"""
Base builder classes for HTML report components.

Provides abstract base class for all component builders and utility classes
for common HTML elements like copy buttons.
"""

from abc import ABC, abstractmethod
from html import escape
from typing import Generic, TypeVar
from urllib.parse import quote

from pydantic import BaseModel

from ..models import BuilderConfig

T = TypeVar("T", bound=BaseModel)


class BaseBuilder(ABC, Generic[T]):
    """Abstract base class for all HTML component builders.

    Builders transform Pydantic data models into HTML string components.
    Each builder is responsible for:
    - Validating input data
    - Escaping HTML content safely
    - Generating well-formed HTML fragments
    - Supporting optional configuration

    Example:
        class MyBuilder(BaseBuilder[MyModel]):
            def build(self, data: MyModel) -> str:
                self.validate(data)
                return f"<div>{self.escape(data.content)}</div>"
    """

    def __init__(self, config: BuilderConfig | None = None):
        """Initialize builder with optional configuration.

        Args:
            config: Optional configuration for customizing output
        """
        self.config = config or BuilderConfig()

    @abstractmethod
    def build(self, data: T) -> str:
        """Build HTML component from data model.

        Args:
            data: Pydantic model containing component data

        Returns:
            HTML string fragment
        """
        pass

    def validate(self, data: T) -> bool:
        """Validate input data before building.

        Args:
            data: Data to validate

        Returns:
            True if valid

        Raises:
            ValueError: If data is None or invalid
        """
        if data is None:
            raise ValueError(f"{self.__class__.__name__}: data cannot be None")
        return True

    @staticmethod
    def escape(text: str | None) -> str:
        """Escape HTML special characters in text.

        Args:
            text: Text to escape

        Returns:
            HTML-escaped text, or empty string if text is None
        """
        if text is None:
            return ""
        return escape(str(text))

    @staticmethod
    def url_encode(path: str) -> str:
        """URL-encode a file path for PyCharm links.

        Args:
            path: File path to encode

        Returns:
            URL-encoded path
        """
        return quote(path)


class CopyButtonBuilder:
    """Utility for building copy button HTML with proper SVG icons.

    Copy buttons display a clipboard icon that changes to a checkmark
    when content is copied. They support tooltips and can optionally
    stop event propagation for nested buttons.
    """

    CLIPBOARD_SVG = '''<svg class="clipboard" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
    </svg>'''

    CHECKMARK_SVG = '''<svg class="checkmark" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polyline points="20 6 9 17 4 12"></polyline>
    </svg>'''

    @classmethod
    def build(cls, tooltip: str, onclick: str, stop_propagation: bool = False) -> str:
        """Build copy button HTML.

        Args:
            tooltip: Tooltip text to display on hover
            onclick: JavaScript function call (without event.stopPropagation())
            stop_propagation: Whether to add event.stopPropagation() for nested buttons

        Returns:
            Complete button HTML string
        """
        onclick_prefix = "event.stopPropagation(); " if stop_propagation else ""

        return f'''<button class="copy-icon-btn" data-tooltip="{tooltip}" onclick="{onclick_prefix}{onclick}">
      {cls.CLIPBOARD_SVG}
      {cls.CHECKMARK_SVG}
    </button>'''


class FileLinkBuilder:
    """Utility for building editor file links.

    Creates links that open files in VS Code or PyCharm based on file extension.
    Python files (.py) open in PyCharm; all other files open in VS Code.
    """

    LINK_ICON = '<span class="link-icon">&#8599;</span>'

    @classmethod
    def build(
        cls,
        file_path: str,
        display_text: str | None = None,
        line_number: int | None = None,
        config: BuilderConfig | None = None
    ) -> str:
        """Build an editor file link.

        Args:
            file_path: Absolute path to the file
            display_text: Text to display (defaults to file_path)
            line_number: Optional line number to open at
            config: Builder configuration

        Returns:
            HTML anchor tag with appropriate editor URL
        """
        config = config or BuilderConfig()
        text = display_text or file_path

        # Determine editor based on file extension
        is_python = any(file_path.endswith(ext) for ext in config.pycharm_extensions)
        editor_type = "pycharm" if is_python else "vscode"
        editor_name = "PyCharm" if is_python else "VS Code"

        # Build URL
        if editor_type == "pycharm":
            url = f"pycharm://open?file={quote(file_path)}"
            if line_number:
                url += f"&line={line_number}"
        else:
            url = f"vscode://file/{file_path}"
            if line_number:
                url += f":{line_number}"

        return (
            f'<a href="{url}" class="file-link {editor_type}" '
            f'title="Open in {editor_name}">{escape(text)}{cls.LINK_ICON}</a>'
        )
