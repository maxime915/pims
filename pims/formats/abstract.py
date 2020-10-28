import re
from abc import abstractmethod, ABC

_CAMEL_TO_SPACE_PATTERN = re.compile(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))')


class AbstractFormat(ABC):
    @classmethod
    def get_identifier(cls, uppercase=True):
        """
        Get the format identifier. It must be unique across all formats.

        Parameters
        ----------
        uppercase: bool
            If the format must be returned in uppercase.
            In practice, comparisons are always done using the uppercase identifier

        Returns
        -------
        identifier: str
            The format identifier
        """
        identifier = cls.__name__.replace('Format', '')
        if uppercase:
            return identifier.upper()
        return identifier

    @classmethod
    def get_name(cls):
        return re.sub(_CAMEL_TO_SPACE_PATTERN, r' \1', cls.get_identifier(False))

    @classmethod
    def get_remarks(cls):
        return str()

    @classmethod
    def get_plugin_name(cls):
        return cls.__module__

    @classmethod
    def is_readable(cls):
        return hasattr(cls, 'read') and callable(cls.read)

    @classmethod
    def is_writable(cls):
        return hasattr(cls, 'write') and callable(cls.write)

    @classmethod
    def is_convertible(cls):
        return hasattr(cls, 'convert') and callable(cls.convert)

    @property
    @abstractmethod
    def width(self):
        pass

    @property
    @abstractmethod
    def height(self):
        pass
