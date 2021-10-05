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

from abc import ABC, abstractmethod

from pims.api.utils.models import HistogramType


class HistogramReaderInterface(ABC):

    @abstractmethod
    def type(self) -> HistogramType:
        pass

    @abstractmethod
    def image_bounds(self):
        """
        Intensity bounds on the whole image (all planes merged).

        Returns
        -------
        mini : int
            The lowest intensity in all image planes
        maxi : int
            The greatest intensity in all image planes
        """
        pass

    @abstractmethod
    def image_histogram(self):
        """
        Intensity histogram on the whole image (all planes merged)

        Returns
        -------
        histogram : array_like (shape: 2^image.bitdepth)
        """
        pass

    @abstractmethod
    def channels_bounds(self):
        """
        Intensity bounds for every channels

        Returns
        -------
        channels_bounds : list of tuple (int, int)
        """
        pass

    @abstractmethod
    def channel_bounds(self, c):
        """
        Intensity bounds for a channel.

        Parameters
        ----------
        c : int
            The image channel index. Index is expected to be valid.

        Returns
        -------
        mini : int
            The lowest intensity for that channel in all image (Z, T) planes
        maxi : int
            The greatest intensity for that channel in all image (Z, T) planes
        """
        pass

    @abstractmethod
    def channel_histogram(self, c):
        """
        Intensity histogram for a channel

        Parameters
        ----------
        c : int
            The image channel index

        Returns
        -------
        histogram : array_like (shape: 2^image.bitdepth)
        """
        pass

    @abstractmethod
    def planes_bounds(self):
        """
        Intensity bounds for every planes

        Returns
        -------
        planes_bounds : list of tuple (int, int)
        """
        pass

    @abstractmethod
    def plane_bounds(self, c, z, t):
        """
        Intensity bounds for a plane

        Parameters
        ----------
        c : int
            The image channel index
        z : int
            The focal plane index
        t : int
            The timepoint index

        Returns
        -------
        mini : int
            The lowest intensity for that plane
        maxi : int
            The greatest intensity for that plane
        """
        pass

    @abstractmethod
    def plane_histogram(self, c, z, t):
        """
        Intensity histogram for a plane

        Returns
        -------
        histogram : array_like (shape: 2^image.bitdepth)
        """
        pass
