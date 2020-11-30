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

import re
from abc import abstractmethod, ABC

from tifffile import lazyattr

from pims.formats.utils.metadata import MetadataStore, ImageMetadata
from pims.formats.utils.pyramid import Pyramid

_CAMEL_TO_SPACE_PATTERN = re.compile(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))')


class PathMatchProxy:
    def __init__(self, path):
        self.path = path

    def get(self, name, delayed_func, *args, **kwargs):
        if not hasattr(self, name):
            setattr(self, name, delayed_func(*args, **kwargs))
        return getattr(self, name)


class AbstractFormat(ABC):
    def __init__(self, path):
        self._path = path

        self._imd = None

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

    @classmethod
    def match(cls, proxypath: PathMatchProxy):
        """
        Identify if it is this format or not.

        Parameters
        ----------
        proxypath : PathMatchProxy
            The path, proxied with some useful results across formats.

        Returns
        -------
        match: boolean
            Whether it is this format
        """
        return False

    @classmethod
    def from_proxy(cls, proxypath):
        return cls(path=proxypath.path)

    @abstractmethod
    def init_standard_metadata(self):
        pass

    @abstractmethod
    def init_complete_metadata(self):
        self._imd.is_complete = True

    def get_image_metadata(self, complete=False):
        if not self._imd:
            self.init_standard_metadata()
        if complete and not self._imd.is_complete:
            self.init_complete_metadata()
        return self._imd

    def get_raw_metadata(self):
        metadata = self.get_image_metadata(True)
        return metadata.to_metadata_store(MetadataStore())

    @lazyattr
    def pyramid(self):
        if not self._imd:
            self.init_standard_metadata()

        p = Pyramid()
        p.insert_tier(self._imd.width, self._imd.height,
                      (self._imd.width, self._imd.height))
        return p
