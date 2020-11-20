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

import json

from collections.abc import MutableMapping
from enum import Enum
from typing import ValuesView, AbstractSet, Tuple


def parse_json(value, raise_exc=False):
    try:
        return json.loads(value)
    except:
        if raise_exc:
            raise
        return None


class JsonParser:
    def __call__(self, value):
        return parse_json(value, True)


def parse_boolean(value, raise_exc=False):
    _true_set = {'yes', 'true', 't', 'y', '1'}
    _false_set = {'no', 'false', 'f', 'n', '0'}

    if value is True or value is False:
        return value
    elif isinstance(value, str):
        value = value.lower()
        if value in _true_set:
            return True
        if value in _false_set:
            return False

    if raise_exc:
        raise ValueError('Expected "%s"' % '", "'.join(_true_set | _false_set))
    return None


class BooleanParser:
    def __call__(self, value):
        return parse_boolean(value, True)


def parse_float(value, raise_exc=False):
    if type(value) == str:
        value = value.replace(",", ".")
    try:
        return float(value)
    except:
        if raise_exc:
            raise
        return None


class FloatParser:
    def __call__(self, value):
        return parse_float(value, True)


class MetadataType(Enum):
    """
    Types for metadata.
    MetadataType names come from API specification.
    """
    def __init__(self, parse_func=str):
        self.parse_func = parse_func

    BOOLEAN = BooleanParser()
    INTEGER = int
    DECIMAL = FloatParser()
    JSON = JsonParser()

    # BASE64 = 6
    # DATE = 7
    # DATETIME = 8

    # must come last (generic)
    STRING = str


class Metadata:
    """
    A metadata from a file (e.g. an image).
    """
    def __init__(self, key, value, dtype=None, namespace=None):
        """
        Initialize a metadata.

        Parameters
        ----------
        key: string
            The name of the metadata
        value: any
            The value of the metadata
        dtype: MetadataType (optional)
            The type of the metadata. If not provided, the type is inferred
            from the value.
        """
        self._key = key
        self._raw_value = str(value)
        self._dtype = dtype if dtype else self.infer_dtype()
        self._parsed_value = self._dtype.parse_func(self._raw_value)
        self._namespace = str(namespace) if namespace is not None else ""

    @property
    def raw_value(self):
        return self._raw_value

    @property
    def parsed_value(self):
        return self._parsed_value

    @property
    def dtype(self) -> MetadataType:
        return self._dtype

    @property
    def key(self) -> str:
        return self._key

    @property
    def namespace(self):
        return self._namespace

    @property
    def namespaced_key(self):
        return "{}.{}".format(self.namespace, self.key) if self.namespace else self.key

    def infer_dtype(self) -> MetadataType:
        for dtype in MetadataType:
            try:
                dtype.parse_func(self._raw_value)
                return dtype
            except (ValueError, TypeError):
                pass
        return MetadataType.STRING

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Metadata) and self.key == o.key \
               and self.parsed_value == o.parsed_value \
               and self.namespace == o.namespace

    def __str__(self):
        return "{}={} ({})".format(self.namespaced_key, self.parsed_value, self.dtype.name)

    def __repr__(self):
        return "{}={} ({})".format(self.namespaced_key, self.parsed_value, self.dtype.name)


class MetadataStore(MutableMapping):
    """
    A store of metadata, extracted from a file (e.g. an image)
    """
    def __init__(self):
        self._data = dict()

    def __delitem__(self, v: str) -> None:
        raise NotImplementedError

    def __setitem__(self, k: str, v: Metadata) -> None:
        self._data[k] = v

    def set(self, key: str, value, dtype=None, namespace=None) -> None:
        """
        Set a metadata in the store.

        Parameters
        ----------
        key: str
            The name of the metadata
        value: any
            The value of the metadata
        dtype: MetadataType (optional)
            The type of the metadata. If not provided, the type is inferred
            from the value.
        namespace: str (optional)
            The metadata namespace
        """
        metadata = Metadata(key, value, dtype, namespace)
        self._data[metadata.namespaced_key] = metadata

    def __getitem__(self, k: str) -> Metadata:
        return self._data[k]

    def get(self, k: str, default=None):
        return self._data.get(k, default)

    def get_value(self, k: str, default=None, parsed=True):
        metadata = self.get(k, None)
        if metadata:
            return metadata.parsed_value if parsed else metadata.raw_value
        return default

    def get_dtype(self, k: str, default=None):
        metadata = self.get(k, None)
        if metadata:
            return metadata.dtype
        return default

    def items(self) -> AbstractSet[Tuple[str, Metadata]]:
        return self._data.items()

    def keys(self) -> AbstractSet[str]:
        return self._data.keys()

    def values(self) -> ValuesView[Metadata]:
        return self._data.values()

    def __contains__(self, o: object) -> bool:
        return o in self._data

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __str__(self) -> str:
        return str(self._data)

    def __repr__(self) -> str:
        return repr(self._data)


class _MetadataStorable:
    def metadata_namespace(self):
        return None

    def to_metadata_store(self, store):
        for attr in self.__dict__:
            if not attr.startswith("_"):
                value = getattr(self, attr)
                if isinstance(value, list):
                    for item in value:
                        if issubclass(type(item), _MetadataStorable):
                            item.to_metadata_store(store)
                elif issubclass(type(value), _MetadataStorable):
                    value.to_metadata_store(store)
                elif value is not None:
                    store.set(attr, value, namespace=self.metadata_namespace())
        return store


class ImageChannel(_MetadataStorable):
    def __init__(self, index=None, emission_wavelength=None, excitation_wavelength=None, samples_per_pixel=None,
                 suggested_name=None):
        self.emission_wavelength = emission_wavelength
        self.excitation_wavelength = excitation_wavelength
        self.index = index
        self.samples_per_pixel = samples_per_pixel
        self.suggested_name = suggested_name

    def metadata_namespace(self):
        return "channel[{}]".format(self.index)


class ImageObjective(_MetadataStorable):
    def __init__(self):
        self.nominal_magnification = None
        self.calibrated_magnification = None

    def metadata_namespace(self):
        return "objective"


class ImageMicroscope(_MetadataStorable):
    def __init__(self):
        self.model = None

    def metadata_namespace(self):
        return "microscope"


class ImageAssociated(_MetadataStorable):
    def __init__(self):
        self.has_thumb = False
        self.has_label = False
        self.has_macro = False

    def metadata_namespace(self):
        return "associated"


class ImageMetadata(_MetadataStorable):
    def __init__(self):
        self._is_complete = False

        self.width = None
        self.height = None
        self.depth = None
        self.n_channels = None
        self.duration = None

        self.pixel_type = None
        self.significant_bits = None

        self.physical_size_x = None
        self.physical_size_y = None
        self.physical_size_z = None
        self.frame_rate = None

        self.acquisition_datetime = None
        self.description = None

        self.channels = list()
        self.objective = ImageObjective()
        self.microscope = ImageMicroscope()
        self.associated = ImageAssociated()

    def set_channel(self, channel):
        self.channels.insert(channel.index, channel)

    def metadata_namespace(self):
        return "image"

    @property
    def is_complete(self):
        return self._is_complete

    @is_complete.setter
    def is_complete(self, value):
        self._is_complete = value
