"""
HTML Report Builder Assets.

This module provides CSS and JavaScript assets for the HTML Report Builder.
All styles and scripts are extracted from the reference implementation.
"""

from .styles import (
    CSS_VARIABLES,
    CSS_BASE,
    CSS_HEADER,
    CSS_TABS,
    CSS_STATUS_BANNER,
    CSS_METADATA,
    CSS_SECTIONS,
    CSS_COPY_BUTTON,
    CSS_EXPECTATIONS,
    CSS_TIMELINE,
    CSS_RESPONSE,
    CSS_DEBUG,
    CSS_ASSESSMENT,
    CSS_FILE_LINKS,
    get_all_css,
)

from .scripts import (
    JS_EDITOR_UTILS,
    JS_TAB_SWITCHING,
    JS_COPY_FUNCTIONS,
    JS_TOGGLE_FUNCTIONS,
    JS_MARKDOWN_RENDERER,
    JS_ASSESSMENT_LOADER,
    JS_INITIALIZATION,
    get_all_scripts,
)


class AssetManager:
    """
    Manager class for HTML report assets.

    Provides convenient access to CSS and JavaScript assets for report generation.
    """

    @staticmethod
    def get_css() -> str:
        """
        Get complete CSS stylesheet.

        Returns:
            Complete CSS as a string, ready to embed in a <style> tag.
        """
        return get_all_css()

    @staticmethod
    def get_scripts() -> str:
        """
        Get complete JavaScript code.

        Returns:
            Complete JavaScript as a string, ready to embed in a <script> tag.
        """
        return get_all_scripts()

    @staticmethod
    def get_style_tag() -> str:
        """
        Get CSS wrapped in a <style> tag.

        Returns:
            CSS wrapped in HTML <style> tag.
        """
        return f"<style>\n{get_all_css()}\n</style>"

    @staticmethod
    def get_script_tag() -> str:
        """
        Get JavaScript wrapped in a <script> tag.

        Returns:
            JavaScript wrapped in HTML <script> tag.
        """
        return f"<script>\n{get_all_scripts()}\n</script>"


__all__ = [
    # CSS constants
    "CSS_VARIABLES",
    "CSS_BASE",
    "CSS_HEADER",
    "CSS_TABS",
    "CSS_STATUS_BANNER",
    "CSS_METADATA",
    "CSS_SECTIONS",
    "CSS_COPY_BUTTON",
    "CSS_EXPECTATIONS",
    "CSS_TIMELINE",
    "CSS_RESPONSE",
    "CSS_DEBUG",
    "CSS_ASSESSMENT",
    "CSS_FILE_LINKS",
    "get_all_css",
    # JavaScript constants
    "JS_EDITOR_UTILS",
    "JS_TAB_SWITCHING",
    "JS_COPY_FUNCTIONS",
    "JS_TOGGLE_FUNCTIONS",
    "JS_MARKDOWN_RENDERER",
    "JS_ASSESSMENT_LOADER",
    "JS_INITIALIZATION",
    "get_all_scripts",
    # Manager class
    "AssetManager",
]
