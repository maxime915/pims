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


def get_first(dict, keys, default=None):
    for k in keys:
        v = dict.get(k)
        if v is not None:
            return v
    return default


def invert(dict):
    return {
        v: k for k, v in dict.items()
    }


def flatten_dict(d, parent_key='', sep='.'):
    items = []
    for k, v in d.items():
        if parent_key:
            if k.startswith('['):
                new_key = parent_key + k
            else:
                new_key = parent_key + sep + k
        else:
            new_key = k
        if isinstance(v, collections.MutableMapping):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
