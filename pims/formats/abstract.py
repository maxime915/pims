import re
from abc import abstractmethod, ABC

from pims.formats.metadata import MetadataStore

_CAMEL_TO_SPACE_PATTERN = re.compile(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))')


class AbstractFormat(ABC):
    def __init__(self, imagepath):
        self._imagepath = imagepath
        self._core_metadata = MetadataStore("CORE")
        self._objective_metadata = MetadataStore("OBJECTIVE")
        self._microscope_metadata = MetadataStore("MICROSCOPE")
        self._associated_metadata = MetadataStore("ASSOCIATED")

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

    @classmethod
    def is_spatial(cls):
        return False

    @classmethod
    def is_spectral(cls):
        return False

    def match(self):
        return False

    @property
    @abstractmethod
    def width(self):
        pass

    @property
    @abstractmethod
    def height(self):
        pass

    @property
    @abstractmethod
    def pixel_type(self):
        pass

    @property
    @abstractmethod
    def significant_bits(self):
        pass

    @property
    def depth(self):
        return 1

    @property
    def duration(self):
        return 1

    @property
    def n_channels(self):
        return 1

    @property
    def physical_size_x(self):
        return None

    @property
    def physical_size_y(self):
        return None

    @property
    def physical_size_z(self):
        return None

    @property
    def frame_rate(self):
        return None

    @property
    def acquisition_datetime(self):
        return None

    @property
    def description(self):
        return None

    @property
    def core_metadata(self):
        return self._core_metadata

    @property
    def objective_metadata(self):
        return self._objective_metadata

    @property
    def microscope_metadata(self):
        return self._microscope_metadata

    @property
    def associated_metadata(self):
        return self._associated_metadata

    def get_raw_metadata(self):
        return MetadataStore("RAW")
