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


class JsonParser:
    def __call__(self, value) -> dict:
        return json.loads(value)


class BooleanParser:
    def __call__(self, value) -> bool:
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

        raise ValueError('Expected "%s"' % '", "'.join(_true_set | _false_set))


json_parser = JsonParser()
boolean_parser = BooleanParser()


class MetadataType(Enum):
    """
    Types for metadata.
    MetadataType names come from API specification.
    """
    def __init__(self, parse_func=str):
        self.parse_func = parse_func

    INTEGER = int
    DECIMAL = float
    BOOLEAN = boolean_parser
    JSON = json_parser

    # BASE64 = 6
    # DATE = 7
    # DATETIME = 8

    # must come last (generic)
    STRING = str


class Metadata:
    """
    A metadata from a file (e.g. an image).
    """
    def __init__(self, name, value, dtype=None):
        """
        Initialize a metadata.

        Parameters
        ----------
        name: string
            The name of the metadata
        value: any
            The value of the metadata
        dtype: MetadataType (optional)
            The type of the metadata. If not provided, the type is inferred
            from the value.
        """
        self._name = name
        self._raw_value = value
        self._dtype = dtype if dtype else self.infer_dtype()
        self._parsed_value = self._dtype.parse_func(self._raw_value)

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
    def name(self) -> str:
        return self._name

    def infer_dtype(self) -> MetadataType:
        for dtype in MetadataType:
            try:
                dtype.parse_func(self._raw_value)
                return dtype
            except ValueError:
                pass
        return MetadataType.STRING

    def __eq__(self, o: object) -> bool:
        return isinstance(o, Metadata) and self.name == o.name \
               and self.parsed_value == o.parsed_value

    def __str__(self):
        return "{}={} ({})".format(self.name, self.parsed_value, self.dtype.name)

    def __repr__(self):
        return "{}={} ({})".format(self.name, self.parsed_value, self.dtype.name)


class MetadataStore(MutableMapping):
    """
    A store of metadata, extracted from a file (e.g. an image)
    """
    def __init__(self, namespace):
        self.namespace = namespace
        self._data = dict()

    def __delitem__(self, v: str) -> None:
        raise NotImplementedError

    def __setitem__(self, k: str, v: Metadata) -> None:
        self._data[k] = v

    def set(self, name: str, value, dtype=None) -> None:
        """
        Set a metadata in the store.

        Parameters
        ----------
        name: str
            The name of the metadata
        value: any
            The value of the metadata
        dtype: MetadataType (optional)
            The type of the metadata. If not provided, the type is inferred
            from the value.
        """
        metadata = Metadata(name, value, dtype)
        self._data[name] = metadata

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
