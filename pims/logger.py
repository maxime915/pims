from logging import LogRecord

from rich.console import ConsoleRenderable
from rich.logging import RichHandler
from rich.text import Text


class PimsHandler(RichHandler):
    def render_message(self, record: LogRecord, message: str) -> "ConsoleRenderable":
        """Render message text in to Text.

        record (LogRecord): logging Record.
        message (str): String cotaining log message.

        Returns:
            ConsoleRenderable: Renderable to display log message.
        """
        use_markup = (
            getattr(record, "markup") if hasattr(record, "markup") else self.markup
        )
        use_highlighter = (
            getattr(record, "highlight") if hasattr(record, "highlight") else self.highlighter
        )
        message_text = Text.from_markup(message) if use_markup else Text(message)
        if use_highlighter:
            message_text = self.highlighter(message_text)
        if self.KEYWORDS:
            message_text.highlight_words(self.KEYWORDS, "logging.keyword")
        return message_text
