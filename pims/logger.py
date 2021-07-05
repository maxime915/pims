import logging
import re
from logging import LogRecord

from rich.console import ConsoleRenderable
from rich.logging import RichHandler
from rich.text import Text

RICH_FORMAT_REGEX = re.compile("[\[].*?[\]]")


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


class StdoutFormatter(logging.Formatter):
    def format(self, record: LogRecord) -> str:
        record.message = re.sub(RICH_FORMAT_REGEX, "", record.getMessage())
        if self.usesTime():
            record.asctime = self.formatTime(record, self.datefmt)
        s = self.formatMessage(record)
        if record.exc_info:
            # Cache the traceback text to avoid converting it multiple times
            # (it's constant anyway)
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
        if record.exc_text:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + record.exc_text
        if record.stack_info:
            if s[-1:] != "\n":
                s = s + "\n"
            s = s + self.formatStack(record.stack_info)
        return s
