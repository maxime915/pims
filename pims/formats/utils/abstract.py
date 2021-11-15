#  * Copyright (c) 2020-2021. Authors: see NOTICE file.
#  *
#  * Licensed under the Apache License, Version 2.0 (the "License");
#  * you may not use this file except in compliance with the License.
#  * You may obtain a copy of the License at
#  *
#  *      http://www.apache.org/licenses/LICENSE-2.0
#  *
#  * Unless required by applicable law or agreed to in writing, software
#  * distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.
from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from functools import cached_property
from typing import Any, Dict, List, Optional, TYPE_CHECKING, Type, Union

from pims.api.exceptions import BadRequestException
from pims.api.utils.models import HistogramType
from pims.cache import SimpleDataCache
from pims.formats.utils.histogram import HistogramReaderInterface
from pims.formats.utils.structures.annotations import ParsedMetadataAnnotation
from pims.formats.utils.structures.metadata import ImageMetadata, MetadataStore
from pims.formats.utils.structures.planes import PlanesInfo
from pims.formats.utils.structures.pyramid import Pyramid

if TYPE_CHECKING:
    from pims.files.file import Path

log = logging.getLogger("pims.formats")

_CAMEL_TO_SPACE_PATTERN = re.compile(r'((?<=[a-z])[A-Z]|(?<!\A)[A-Z](?=[a-z]))')


class CachedDataPath(SimpleDataCache):
    """
    A cache associated to a path.

    Technical details: It would be more meaningful to have `CachedDataPath` inheriting
    from `SimpleDataCache` and `Path` as Python allows multiple inheritance. Other
    meaningful implementation could be to have `CachedDataPath` that extends `Path` and
    have an attribute `cache`. However, both solutions are impossible because they
    cause circular imports.
    """
    def __init__(self, path: Path):
        super().__init__()
        self.path = path


class AbstractChecker(ABC):
    """
    Base checker. All format checkers must extend this class.
    """

    @classmethod
    @abstractmethod
    def match(cls, pathlike: Union[Path, CachedDataPath]) -> bool:
        """Whether the path is in this format or not."""
        pass


class AbstractParser(ABC):
    """
    Base parser. All format parsers must extend this class.
    """

    def __init__(self, format: AbstractFormat):
        self.format = format

    @abstractmethod
    def parse_main_metadata(self) -> ImageMetadata:
        """
        Parse minimal set of required metadata for any PIMS request.
        This method must be as fast as possible.

        Main metadata that must be parsed by this method are:
        * width
        * height
        * depth
        * duration
        * n_channels
        * n_channels_per_read
        * n_distinct_channels
        * pixel_type
        * significant_bits
        * for every channel:
            * index
            * color (can be None)
            * suggested_name (can be None, used to infer color)

        It is allowed to parse more metadata in this method if it does not
        introduce overhead.
        """
        pass

    @abstractmethod
    def parse_known_metadata(self) -> ImageMetadata:
        """
        Parse all known standardised metadata. In practice, this method
        completes the image metadata object partially filled by
        `parse_main_metadata`.

        This method should set `imd.is_complete` to True before returning `imd`.
        """
        return self.format.main_imd

    @abstractmethod
    def parse_raw_metadata(self) -> MetadataStore:
        """
        Parse all raw metadata in a generic store. Raw metadata are not
        standardised and highly depend on underlying parsed format.

        Raw metadata MUST NOT be used by PIMS for processing.
        This method is expected to be SLOW.
        """
        return MetadataStore()

    def parse_pyramid(self) -> Pyramid:
        """
        Parse pyramid (and tiers) from format metadata. In all cases, the
        pyramid must have at least one tier (i.e. the image at full resolution).

        Arbitrary information useful for readers can be stored for each tier
        (e.g.: a TIFF page index).

        This method must be as fast as possible.
        """
        imd = self.format.main_imd
        p = Pyramid()
        p.insert_tier(imd.width, imd.height, (imd.width, imd.height))
        return p

    def parse_planes(self) -> PlanesInfo:
        """
        Parse plane information from format metadata. In all cases, there is
        at least one plane (0, 0, 0).

        Arbitrary information useful for readers can be stored for each plane
        (e.g.: a TIFF page index).

        This method must be as fast as possible.
        """
        imd = self.format.main_imd
        pi = PlanesInfo(imd.n_channels, imd.depth, imd.duration)
        return pi

    def parse_annotations(self) -> List[ParsedMetadataAnnotation]:
        """
        Parse annotations stored in image format metadata, together with
        optional terms and properties.
        """
        return []


class AbstractReader(ABC):
    """
    Base reader. All format readers must extend this class.
    """
    def __init__(self, format: AbstractFormat):
        self.format = format

    def read_thumb(
        self, out_width: int, out_height: int, precomputed: bool = None,
        c: Optional[int] = None, z: Optional[int] = None, t: Optional[int] = None
    ) -> object:
        """
        Get the nearest image thumbnail to asked output dimensions.

        Output dimensions are best-effort, that is, depending on the format
        and the underlying library used to extract pixels from the image format,
        it may or may not be possible to return a thumbnail at the asked output
        dimensions. The implementation SHOULD try to return the nearest possible
        thumbnail using format capabilities (such as shrink on load features)
        but MUST NOT perform any resize operation after read (in that case, an
        optimized resize operator is used in post-processing).

        Parameters
        ----------
        out_width
            The asked output width (best-effort)
        out_height
            The asked output height (best-effort)
        precomputed
            Whether use precomputed thumbnail stored in the file if available.
            Retrieving precomputed thumbnail should be faster than computing
            the thumbnail from scratch (for multi-giga pixels images), but there
            is no guarantee the precomputed thumb has the same quality.
        c
            The asked channel index (best-effort).
            If not set, all channels are considered.
        z
            The asked z-slice index. Image formats without Z-stack support
            can safely ignore this parameter. Behavior is undetermined if `z`
            is not set for an image format with Z-stack support.
        t
            The asked timepoint index. Image formats without time support
            can safely ignore this parameter. Behavior is undetermined if `t`
            is not set for an image format with time support.

        Returns
        -------

        """
        raise NotImplementedError()

    def read_window(self, region, out_width, out_height, c=None, z=None, t=None):
        raise NotImplementedError()

    def read_tile(self, tile, c=None, z=None, t=None):
        raise NotImplementedError()


class AbstractHistogramReader(HistogramReaderInterface, ABC):
    def __init__(self, format):
        self.format = format


class NullHistogramReader(AbstractHistogramReader):
    # @abstractmethod
    def type(self) -> HistogramType:
        return HistogramType.FAST

    # @abstractmethod
    def image_bounds(self):
        log.warning(
            f"[orange]Impossible {self.format.path} to compute "
            f"image histogram bounds. Default values used."
        )
        return 0, 2 ** self.format.main_imd.significant_bits

    # @abstractmethod
    def image_histogram(self):
        raise BadRequestException(detail=f"No histogram found for {self.format.path}")

    # @abstractmethod
    def channels_bounds(self):
        log.warning(
            f"[orange]Impossible {self.format.path} to compute "
            f"channels histogram bounds. Default values used."
        )
        return [(0, 2 ** self.format.main_imd.significant_bits)] * self.format.main_imd.n_channels

    # @abstractmethod
    def channel_bounds(self, c):
        log.warning(
            f"[orange]Impossible {self.format.path} to compute "
            f"channel histogram bounds. Default values used."
        )
        return 0, 2 ** self.format.main_imd.significant_bits

    # @abstractmethod
    def channel_histogram(self, c):
        raise BadRequestException(detail=f"No histogram found for {self.format.path}")

    # @abstractmethod
    def planes_bounds(self):
        log.warning(
            f"[orange]Impossible {self.format.path} to compute "
            f"plane histogram bounds. Default values used."
        )
        return [(0, 2 ** self.format.main_imd.significant_bits)] * self.format.main_imd.n_planes

    # @abstractmethod
    def plane_bounds(self, c, z, t):
        log.warning(
            f"[orange]Impossible {self.format.path} to compute "
            f"plane histogram bounds. Default values used."
        )
        return 0, 2 ** self.format.main_imd.significant_bits

    # @abstractmethod
    def plane_histogram(self, c, z, t):
        raise BadRequestException(detail=f"No histogram found for {self.format.path}")


class AbstractConvertor(ABC):
    def __init__(self, source):
        self.source = source

    def convert(self, dest_path):
        raise NotImplementedError()

    def conversion_format(self):
        raise NotImplementedError()


class AbstractFormat(ABC, SimpleDataCache):
    """
    Base format. All image formats must extend this class.
    """
    checker_class: Type[AbstractChecker] = None
    parser_class: Type[AbstractParser] = None
    reader_class: Type[AbstractReader] = None
    convertor_class: Type[AbstractConvertor] = None

    histogram_reader_class: Type[AbstractHistogramReader] = None

    def __init__(self, path: Path, existing_cache: Dict[str, Any] = None):
        """
        Initialize an image in this format. It does nothing until some
        parsing or reading methods are called.

        Parameters
        ----------
        path
            The image path
        existing_cache
            A cache of data related to the image that have been previously
            computed and that could be used again in the future.
            In practice, it is used to collect data computed during matching
            (format identification) that can be used again in parser or reader.
        """
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
    def get_identifier(cls, uppercase: bool = True) -> str:
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
    def get_name(cls) -> str:
        """Get the format name in a human-readable way."""
        return re.sub(_CAMEL_TO_SPACE_PATTERN, r' \1', cls.get_identifier(False))

    @classmethod
    def get_remarks(cls) -> str:
        """Get format remarks in a human-readable way."""
        return str()

    @classmethod
    def get_plugin_name(cls) -> str:
        """Get PIMS format plugin name adding this format."""
        return '.'.join(cls.__module__.split('.')[:-1])

    @classmethod
    def is_readable(cls) -> bool:
        """Whether PIMS can read images in this format."""
        return cls.reader_class is not None

    @classmethod
    def is_writable(cls):  # TODO
        return False

    @classmethod
    def is_convertible(cls) -> bool:
        """Whether PIMS can convert images in this format into another one."""
        return cls.convertor_class is not None

    @classmethod
    def is_spatial(cls) -> bool:
        """Whether this format is adapted for spatial data requests."""
        return False

    @classmethod
    def is_spectral(cls) -> bool:
        """Whether this format is adapted for spectral data requests."""
        return False

    @classmethod
    def match(cls, cached_path: CachedDataPath) -> bool:
        """
        Identify if it is this format or not.

        Parameters
        ----------
        cached_path : CachedDataPath
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
    def from_proxy(cls, cached_path: CachedDataPath) -> AbstractFormat:
        return cls(path=cached_path.path, existing_cache=cached_path.cache)

    @classmethod
    def from_path(cls, path: Path) -> AbstractFormat:
        return cls(path=path)

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    @property
    def path(self) -> Path:
        return self._path

    @property
    def media_type(self) -> str:
        return "image"

    # Conversion

    @cached_property
    def need_conversion(self) -> bool:
        """
        Whether the image in this format needs to be converted to another one.
        Decision can be made based on the format metadata.
        """
        return True

    def conversion_format(self) -> Optional[AbstractFormat]:
        """
        Get the format to which the image in this format will be converted,
        if needed.
        """
        if self.convertor:
            return self.convertor.conversion_format()
        else:
            return None

    def convert(self, dest_path: Path) -> bool:
        """
        Convert the image in this format to another one at a given destination
        path.

        Returns
        -------
        result
            Whether the conversion succeeded or not
        """
        if self.convertor:
            return self.convertor.convert(dest_path)
        else:
            raise NotImplementedError()

    # Metadata parsing

    @cached_property
    def main_imd(self) -> ImageMetadata:
        """
        Get main image metadata, that is, required metadata to process
        any request.

        It is possible that other non-required metadata have been populated.
        """
        return self.parser.parse_main_metadata()

    @cached_property
    def full_imd(self) -> ImageMetadata:
        """
        Get full image metadata, that is, all known and standardised metadata.
        `self.full_imd.is_complete` should be true.
        """
        return self.parser.parse_known_metadata()

    @cached_property
    def raw_metadata(self) -> MetadataStore:
        """
        Get all raw metadata in a generic store. Raw metadata are not
        standardised and highly depend on underlying parsed format.

        Raw metadata MUST NOT be used by PIMS for processing.
        """
        return self.parser.parse_raw_metadata()

    @cached_property
    def pyramid(self) -> Pyramid:
        """
        Get image format pyramid. There is always at least one tier (the
        pyramid basis).
        """
        return self.parser.parse_pyramid()

    @cached_property
    def planes_info(self) -> PlanesInfo:
        """
        Information about each plane.
        """
        return self.parser.parse_planes()

    @cached_property
    def annotations(self) -> List[ParsedMetadataAnnotation]:
        """
        Get annotations stored in image format metadata.
        """
        return self.parser.parse_annotations()

    @cached_property
    def histogram(self):  # TODO
        return self.histogram_reader

    @cached_property
    def main_path(self):  # TODO: seem to be useless
        return self.path


