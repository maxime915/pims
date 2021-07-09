# * Copyright (c) 2020. Authors: see NOTICE file.
# *
# * Licensed under the Apache License, Version 2.0 (the "License");
# * you may not use this file except in compliance with the License.
# * You may obtain a copy of the License at
# *
# *      http://www.apache.org/licenses/LICENSE-2.0
# *
# * Unless required by applicable law or agreed to in writing, software
# * distributed under the License is distributed on an "AS IS" BASIS,
# * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# * See the License for the specific language governing permissions and
# * limitations under the License.
import copy
import logging
import re
from abc import abstractmethod, ABC
from functools import cached_property
from typing import Type

from pims.api.exceptions import BadRequestException
from pims.api.utils.models import HistogramType
from pims.formats.utils.histogram import HistogramReaderInterface
from pims.formats.utils.metadata import MetadataStore
from pims.formats.utils.pyramid import Pyramid


log = logging.getLogger("pims.formats")

_CAMEL_TO_SPACE_PATTERN = re.compile(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))')


class CachedData:
    def __init__(self, existing_cache=None):
        self._cache = dict()

        if existing_cache is dict:
            self._cache = copy.deepcopy(existing_cache)

    def cache_value(self, key, value, force=False):
        if force or key not in self._cache:
            self._cache[key] = value

    def cache_func(self, key, delayed_func, *args, **kwargs):
        self.cache_value(key, delayed_func(*args, **kwargs))

    def get_cached(self, key, delayed_func, *args, **kwargs):
        if key not in self._cache:
            self.cache_func(key, delayed_func, *args, **kwargs)
        return self._cache[key]

    @property
    def cache(self):
        return self._cache

    @property
    def cached_keys(self):
        return self._cache.keys()

    def is_in_cache(self, key):
        return key in self._cache

    def clear_cache(self):
        self._cache.clear()


class CachedPathData(CachedData):
    def __init__(self, path):
        super().__init__()
        self.path = path


class AbstractChecker(ABC):
    @classmethod
    @abstractmethod
    def match(cls, pathlike):
        pass


class AbstractParser(ABC):
    def __init__(self, format):
        self.format = format

    @abstractmethod
    def parse_main_metadata(self):
        pass

    @abstractmethod
    def parse_known_metadata(self):
        return self.format.main_imd

    @abstractmethod
    def parse_raw_metadata(self):
        return MetadataStore()

    def parse_pyramid(self):
        imd = self.format.main_imd
        p = Pyramid()
        p.insert_tier(imd.width, imd.height, (imd.width, imd.height))
        return p


class AbstractReader(ABC):
    def __init__(self, format):
        self.format = format

    def read_thumb(self, out_width, out_height, precomputed=None, c=None, z=None, t=None):
        raise NotImplementedError()

    def read_window(self, region, out_width, out_height, c=None, z=None, t=None):
        raise NotImplementedError()

    def read_tile(self, tile, c=None, z=None, t=None):
        raise NotImplementedError()


class AbstractHistogramReader(HistogramReaderInterface, ABC):
    def __init__(self, format):
        self.format = format


class NullHistogramReader(AbstractHistogramReader):
    @abstractmethod
    def type(self) -> HistogramType:
        return HistogramType.FAST

    @abstractmethod
    def image_bounds(self):
        log.warning(f"[orange]Impossible {self.format.path} to compute "
                    f"image histogram bounds. Default values used.")
        return 0, 2 ** self.format.main_imd.significant_bits

    @abstractmethod
    def image_histogram(self):
        raise BadRequestException(detail=f"No histogram found for {self.format.path}")

    @abstractmethod
    def channels_bounds(self):
        log.warning(f"[orange]Impossible {self.format.path} to compute "
                    f"channels histogram bounds. Default values used.")
        return [(0, 2 ** self.format.main_imd.significant_bits)] * self.format.main_imd.n_channels

    @abstractmethod
    def channel_bounds(self, c):
        log.warning(f"[orange]Impossible {self.format.path} to compute "
                    f"channel histogram bounds. Default values used.")
        return 0, 2 ** self.format.main_imd.significant_bits

    @abstractmethod
    def channel_histogram(self, c):
        raise BadRequestException(detail=f"No histogram found for {self.format.path}")

    @abstractmethod
    def planes_bounds(self):
        log.warning(f"[orange]Impossible {self.format.path} to compute "
                    f"plane histogram bounds. Default values used.")
        return [(0, 2 ** self.format.main_imd.significant_bits)] * self.format.main_imd.n_planes

    @abstractmethod
    def plane_bounds(self, c, z, t):
        log.warning(f"[orange]Impossible {self.format.path} to compute "
                    f"plane histogram bounds. Default values used.")
        return 0, 2 ** self.format.main_imd.significant_bits

    @abstractmethod
    def plane_histogram(self, c, z, t):
        raise BadRequestException(detail=f"No histogram found for {self.format.path}")


class AbstractConvertor(ABC):
    def __init__(self, source):
        self.source = source

    def convert(self, dest_path):
        raise NotImplementedError()

    def conversion_format(self):
        raise NotImplementedError()


class AbstractFormat(ABC, CachedData):
    checker_class: Type[AbstractChecker] = None
    parser_class: Type[AbstractParser] = None
    reader_class: Type[AbstractReader] = None
    convertor_class: Type[AbstractConvertor] = None

    histogram_reader_class: Type[AbstractHistogramReader] = None

    def __init__(self, path, existing_cache=None):
        self._path = path
        super(AbstractFormat, self).__init__(existing_cache)

        self._enabled = False

        self.parser = self.parser_class(self)
        self.reader = self.reader_class(self)
        self.convertor = self.convertor_class(self) if self.convertor_class else None

        self.histogram_reader = self.histogram_reader_class(self)

    @classmethod
    def init(cls):
        """
        Initialize the format, such that all third-party libs are ready.
        """
        pass

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
        return '.'.join(cls.__module__.split('.')[:-1])

    @classmethod
    def is_readable(cls):
        return cls.reader_class is not None

    @classmethod
    def is_writable(cls):
        return False

    @classmethod
    def is_convertible(cls):
        return False

    @classmethod
    def is_spatial(cls):
        return False

    @classmethod
    def is_spectral(cls):
        return False

    @classmethod
    def match(cls, cached_path: CachedPathData):
        """
        Identify if it is this format or not.

        Parameters
        ----------
        cached_path : CachedPathData
            The path, proxied with some useful results across formats.

        Returns
        -------
        match: boolean
            Whether it is this format
        """
        if cls.checker_class:
            return cls.checker_class.match(cached_path)
        return False

    @classmethod
    def from_proxy(cls, cached_path):
        return cls(path=cached_path.path, existing_cache=cached_path.cache)

    @classmethod
    def from_path(cls, path):
        return cls(path=path)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    @property
    def path(self):
        return self._path

    # Metadata parsing

    @cached_property
    def need_conversion(self):
        return True

    def convert(self, dest_path):
        if self.convertor:
            return self.convertor.convert(dest_path)
        else:
            raise NotImplementedError()

    def conversion_format(self):
        if self.convertor:
            return self.convertor.conversion_format()
        else:
            return None

    @cached_property
    def main_imd(self):
        return self.parser.parse_main_metadata()

    @cached_property
    def full_imd(self):
        return self.parser.parse_known_metadata()

    @cached_property
    def raw_metadata(self):
        return self.parser.parse_raw_metadata()

    @cached_property
    def pyramid(self):
        return self.parser.parse_pyramid()

    @cached_property
    def histogram(self):
        return self.histogram_reader

    @cached_property
    def main_path(self):
        return self.path
