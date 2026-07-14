from collections.abc import Mapping
from typing import Any, ClassVar

from html5tagger import Document, E, HTML, Template
from tracerite import html_traceback, inspector
from tracerite.html import PAGE_STYLE, Header, javascript, style

from sanic import __version__ as VERSION
from sanic.application.logo import SVG_LOGO_SIMPLE
from sanic.request import Request

from .base import BasePage


# Avoid showing the request in the traceback variable inspectors
inspector.blacklist_types += (Request,)

ENDUSER_TEXT = """\
We're sorry, but it looks like something went wrong. Please try refreshing \
the page or navigating back to the homepage. If the issue persists, our \
technical team is working to resolve it as soon as possible. We apologize \
for the inconvenience and appreciate your patience.\
"""


class ErrorPage(BasePage):
    """Page for displaying an error."""

    _template: ClassVar[Template | None] = None

    def __init__(
        self,
        debug: bool,
        title: str,
        text: str,
        request: Request,
        exc: Exception,
    ) -> None:
        super().__init__(debug)
        name = request.app.name.replace("_", " ").strip()
        if name.islower():
            name = name.title()
        self.TITLE = f"Application {name} cannot handle your request"
        self.HEADING = E("Application ").strong(name)(
            " cannot handle your request"
        )
        self.title = title
        self.text = text
        self.request = request
        self.exc = exc
        self.details_open = not getattr(exc, "quiet", False)

    def _header(self) -> HTML:
        """Sanic site-wide header with the application heading."""
        with E.header as header:
            header.div(self.HEADING or self.TITLE)
        return HTML(header)

    def _footer(self) -> HTML:
        """Sanic footer with logo, version, and help links."""
        with E.footer as footer:
            footer.div("powered by")
            with footer.div:
                footer.a(
                    HTML(SVG_LOGO_SIMPLE),
                    href="https://sanic.dev",
                    target="_blank",
                    referrerpolicy="no-referrer",
                )
            if self.debug:
                footer.div(f"Version {VERSION}")
                with footer.div:
                    for idx, (title, href) in enumerate(
                        (
                            ("Docs", "https://sanic.dev"),
                            ("Help", "https://sanic.dev/en/help.html"),
                            ("GitHub", "https://github.com/sanic-org/sanic"),
                        )
                    ):
                        if idx > 0:
                            footer(" | ")
                        footer.a(
                            title,
                            href=href,
                            target="_blank",
                            referrerpolicy="no-referrer",
                        )
                footer.div("DEBUG mode")
        return HTML(footer)

    def _body(self) -> None:
        """Not used; ErrorPage renders via the TraceRite Page template."""

    def _content(self) -> HTML:
        """Main content: context, end-user message, or debug details."""
        debug = self.request.app.debug
        route_name = self.request.name or "[route not found]"
        content = E.div()

        # Show context details if available on the exception
        context = getattr(self.exc, "context", None)
        if context:
            self._key_value_table(
                content, "Issue context", "exception-context", context
            )

        if not debug:
            with content.div(id="enduser"):
                content.p(ENDUSER_TEXT).p.a("Front Page", href="/")
            return HTML(content)

        # Show additional details in debug mode,
        # open by default for 500 errors
        with content.details(open=self.details_open, class_="smalltext"):
            # Show extra details if available on the exception
            extra = getattr(self.exc, "extra", None)
            if extra:
                self._key_value_table(
                    content, "Issue extra data", "exception-extra", extra
                )

            content.summary(
                "Details for developers (Sanic debug mode only)"
            )
            if self.exc:
                with content.div(class_="exception-wrapper"):
                    content.h2(f"Exception in {route_name}:")
                    content(
                        html_traceback(self.exc, include_js_css=False)
                    )

            self._key_value_table(
                content,
                f"{self.request.method} {self.request.path}",
                "request-headers",
                self.request.headers,
            )

        return HTML(content)

    def _key_value_table(
        self,
        doc: Any,
        title: str,
        table_id: str,
        data: Mapping[str, Any],
    ) -> None:
        with doc.div(class_="key-value-display"):
            doc.h2(title)
            with doc.dl(id=table_id, class_="key-value-table smalltext"):
                for key, value in data.items():
                    # Reading values may cause a new exception, so suppress it
                    try:
                        value = str(value)
                    except Exception:
                        value = E.em("Unable to display value")
                    doc.dt.span(key, class_="nobr key").span(": ").dd(
                        value
                    )

    def render(self) -> str:
        """Render the error page using TraceRite's Page template.

        Sanic-specific styling and extra information (context, request
        headers, footer links, etc.) are injected into the template slots.
        """
        cls = self.__class__
        if cls._template is None:
            cls._template = Template(
                Document(E.Title, lang="en", id="sanic")
                .style(style)
                .style(PAGE_STYLE)
                .style(HTML(self.CSS))
                .script(javascript)
                .Header
                .main(E.Heading.Content)
                .Footer
            )

        return str(
            self._template(
                Title=self.TITLE,
                Header=self._header(),
                Heading=Header(
                    Heading=E("⚠️ ")(self.title), Ingress=self.text
                ),
                Content=self._content(),
                Footer=self._footer(),
            )
        )
