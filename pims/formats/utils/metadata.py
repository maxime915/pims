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
import collections
import json

from datetime import datetime, date, time
from enum import Enum
from typing import ValuesView, AbstractSet, Tuple


def parse_json(value, raise_exc=False):
    try:
        return json.loads(value)
    except:
        if raise_exc:
            raise
        return None


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


def parse_float(value, raise_exc=False):
    if type(value) == str:
        value = value.replace(",", ".")
    try:
        return float(value)
    except:
        if raise_exc:
            raise
        return None


def parse_datetime(value, formats=None, raise_exc=False):
    if formats is None:
        formats = [
            "%Y:%m:%d %H:%M:%S",
            "%m/%d/%y %H:%M:%S"
        ]

    for format in formats:
        try:
            return datetime.strptime(value, format)
        except (ValueError, TypeError):
            continue
    if raise_exc:
        raise ValueError
    return None


def parse_bytes(value, encoding=None, errors='strict', raise_exc=False):
    """Return Unicode string from encoded bytes."""
    try:
        if encoding is not None:
            return value.decode(encoding, errors)
        try:
            return value.decode('utf-8', errors)
        except UnicodeDecodeError:
            return value.decode('cp1252', errors)
    except Exception:
        if raise_exc:
            raise ValueError
        return None


class MetadataType(Enum):
    """
    Types for metadata.
    MetadataType names come from API specification.
    """
    def __init__(self, python_type=str):
        self.python_type = python_type

    BOOLEAN = bool
    INTEGER = int
    DECIMAL = float
    JSON = dict
    LIST = list
    DATE = date
    TIME = time
    DATETIME = datetime
    STRING = str
    UNKNOWN = type(None)


class Metadata:
    """
    A metadata from a file (e.g. an image).
    """
    def __init__(self, key, value, namespace=""):
        """
        Initialize a metadata.

        Parameters
        ----------
        key: str
            The name of the metadata
        value: any
            The value of the metadata
        namespace: str
            The namespace of the key-value pair.

        All attributes are read-only.
        """
        self._key = key
        self._value = value
        self._namespace = namespace.upper()
        self._metadata_type = self.infer_metadata_type()

    @property
    def value(self):
        return self._value

    @property
    def key(self) -> str:
        return self._key

    @property
    def namespace(self):
        return self._namespace

    @property
    def namespaced_key(self):
        return "{}.{}".format(self.namespace, self.key) if self.namespace else self.key

    @property
    def metadata_type(self) -> MetadataType:
        return self._metadata_type

    def infer_metadata_type(self):
        for mt in MetadataType:
            if type(self._value) == mt.python_type:
                return mt
        return MetadataType.UNKNOWN

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Metadata) and self.key == o.key \
               and self.value == o.value \
               and self.namespace == o.namespace

    def __str__(self):
        return "{}={} ({})".format(self.namespaced_key, str(self.value), self.metadata_type.name)

    def __repr__(self):
        return "{}={} ({})".format(self.namespaced_key, str(self.value), self.metadata_type.name)


class MetadataStore:
    """
    A set of metadata stores, extracted from a file (e.g. an image).
    Nested dict like interface.
    1st level dict represents namespaced stores.
    2nd level dicts are metadata dictionaries for each namespace.
    """
    def __init__(self):
        self._namedstores = dict()

    @staticmethod
    def _split_namespaced_key(namespaced_key):
        split = namespaced_key.split('.', 1)
        return ("", namespaced_key) if len(split) < 2 else split

    def set(self, namespaced_key, value, namespace=None) -> None:
        """
        Set a metadata in the store.

        Parameters
        ----------
        namespaced_key: str
            The name of the metadata, starting with its namespace. Namespace and key are dot-separated.
        value: any
            The value of the metadata
        namespace: str, optional
            If given, prepend the namespaced_key with this namespace
        """
        if namespace:
            namespaced_key = "{}.{}".format(namespace, namespaced_key)
        namespace, key = self._split_namespaced_key(namespaced_key)
        metadata = Metadata(key, value, namespace)
        store = self._namedstores.get(metadata.namespace, dict())
        store[key] = metadata
        self._namedstores[metadata.namespace] = store

    def get_namedstore(self, namespace, default=None):
        return self._namedstores.get(namespace.upper(), default)

    def get(self, namespaced_key, default=None):
        namespace, key = self._split_namespaced_key(namespaced_key)
        store = self.get_namedstore(namespace)
        if store:
            return store.get(key, default)
        return default

    def get_value(self, namespaced_key, default=None):
        metadata = self.get(namespaced_key, None)
        if metadata:
            return metadata.value
        return default

    def get_metadata_type(self, namespaced_key, default=None):
        metadata = self.get(namespaced_key, None)
        if metadata:
            return metadata.metadata_type
        return default

    @staticmethod
    def _flatten(d, parent_key='', sep='.'):
        items = []
        for k, v in d.items():
            new_key = parent_key + sep + k if parent_key else k
            if isinstance(v, collections.MutableMapping):
                items.extend(MetadataStore._flatten(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def flatten(self):
        return self._flatten(self._namedstores)

    def items(self) -> AbstractSet[Tuple[str, Metadata]]:
        return self.flatten().items()

    def keys(self) -> AbstractSet[str]:
        return self.flatten().keys()

    def values(self) -> ValuesView[Metadata]:
        return self.flatten().values()

    def __contains__(self, o: object) -> bool:
        if type(o) == Metadata:
            return self.get(o.namespaced_key) is not None
        return o in self._namedstores

    def __len__(self) -> int:
        return len(self._namedstores)

    def __iter__(self):
        return iter(self._namedstores)

    def __str__(self) -> str:
        return str(self._namedstores)

    def __repr__(self) -> str:
        return repr(self._namedstores)


class _MetadataStorable:
    def metadata_namespace(self):
        return ""

    def to_metadata_store(self, store):
        for key in self.__dict__:
            if not key.startswith("_"):
                value = getattr(self, key)
                if isinstance(value, list):
                    for item in value:
                        if issubclass(type(item), _MetadataStorable):
                            item.to_metadata_store(store)
                elif issubclass(type(value), _MetadataStorable):
                    value.to_metadata_store(store)
                elif value is not None:
                    store.set(key, value, namespace=self.metadata_namespace())
        return store


class ImageChannel(_MetadataStorable):
    def __init__(self, index=None, emission_wavelength=None,
                 excitation_wavelength=None, suggested_name=None):
        self.emission_wavelength = emission_wavelength
        self.excitation_wavelength = excitation_wavelength
        self.index = index
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
