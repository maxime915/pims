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
import re
from abc import abstractmethod, ABC
from functools import cached_property

from pims.formats.utils.metadata import MetadataStore
from pims.formats.utils.pyramid import Pyramid

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


class CachedPathData(CachedData):
    def __init__(self, path):
        super().__init__()
        self.path = path


class AbstractFormat(ABC, CachedData):
    checker_class = None
    parser_class = None
    reader_class = None
    histogramer_class = None

    def __init__(self, path, existing_cache=None):
        self._path = path
        super(AbstractFormat, self).__init__(existing_cache)

        self._enabled = False

        self.parser = self.parser_class(self)
        self.reader = self.reader_class(self)
        self.histogramer = self.histogramer_class(self)

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
    def channels_stats(self):
        return self.histogramer.compute_channels_stats()


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


class AbstractHistogramManager(ABC):
    def __init__(self, format):
        self.format = format

    @abstractmethod
    def compute_channels_stats(self):
        pass
