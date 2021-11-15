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
from typing import Any


def split_tuple(tuple_: Any, index: int) -> Any:
    if type(tuple_) == tuple:
        return tuple_[index]
    else:
        return tuple_


def find_first_available_int(values, mini=0, maxi=100) -> int:
    """
    Find first available integer between bounds which is not in a list.

    Parameters
    ----------
    values : list of int, array-like
        A list of unavailable integers.
    mini : int (optional)
        Minimum possible integer (inclusive).
    maxi : int (optional)
        Maximum possible integer (exclusive).

    Returns
    -------
    available : int

    Raises
    ------
    ValueError
        If there is no available integer.
    """
    for i in range(mini, maxi):
        if i not in values:
            return i

    raise ValueError("There is no available integer.")


def ensure_list(value: Any) -> list:
    """
    Ensure it is a list.

    Parameters
    ----------
    value : any
        Value to convert as a list

    Returns
    -------
    list
        The value converted as a list if it is not already the case.
    """
    if value is not None:
        return value if type(value) is list else [value]
    return []
