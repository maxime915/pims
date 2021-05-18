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
from functools import cached_property

from pims.api.exceptions import NoMatchingFormatProblem
from pims.files.file import Path
from pims.formats.utils.pyramid import normalized_pyramid


class Image(Path):
    def __init__(self, *pathsegments, factory=None):
        super().__init__(*pathsegments)

        _format = factory.match(self) if factory else None
        if _format is None:
            raise NoMatchingFormatProblem(self)
        else:
            self._format = _format

    @property
    def format(self):
        return self._format

    @property
    def width(self):
        return self._format.main_imd.width

    @property
    def physical_size_x(self):
        return self._format.full_imd.physical_size_x

    @property
    def height(self):
        return self._format.main_imd.height

    @property
    def physical_size_y(self):
        return self._format.full_imd.physical_size_y

    @property
    def depth(self):
        return self._format.main_imd.depth

    @property
    def physical_size_z(self):
        return self._format.full_imd.physical_size_z

    @property
    def duration(self):
        return self._format.main_imd.duration

    @property
    def frame_rate(self):
        return self._format.main_imd.frame_rate

    @property
    def n_channels(self):
        return self._format.main_imd.n_channels

    @property
    def n_intrinsic_channels(self):
        return self._format.main_imd.n_intrinsic_channels

    @property
    def n_planes(self):
        return self._format.main_imd.n_planes

    @property
    def pixel_type(self):
        return self._format.main_imd.pixel_type

    @property
    def significant_bits(self):
        return self._format.main_imd.significant_bits

    @property
    def acquisition_datetime(self):
        return self._format.full_imd.acquisition_datetime

    @property
    def description(self):
        return self._format.full_imd.description

    @property
    def channels(self):
        return self._format.full_imd.channels

    @property
    def objective(self):
        return self._format.full_imd.objective

    @property
    def microscope(self):
        return self._format.full_imd.microscope

    @property
    def associated_thumb(self):
        return self._format.full_imd.associated_thumb
    
    @property
    def associated_label(self):
        return self._format.full_imd.associated_label
    
    @property
    def associated_macro(self):
        return self._format.full_imd.associated_macro

    @property
    def raw_metadata(self):
        return self._format.raw_metadata

    @property
    def pyramid(self):
        return self._format.pyramid

    @cached_property
    def normalized_pyramid(self):
        return normalized_pyramid(self.width, self.height)

    @cached_property
    def is_pyramid_normalized(self):
        return self.pyramid == self.normalized_pyramid

    def channel_stats(self, c):
        return self.channels_stats().get(c)

    def channels_stats(self):
        return self._format.channels_stats

    def tile(self, tile_region, c=None, z=None, t=None):
        """
        Get tile at specified level and tile index for all (C,Z,T) combinations.

        Returns
        ------
        tile: image-like (PILImage, VIPSImage, numpy array)
            The tile (dimensions: tile_size x tile_size x len(c) x len(z) x len(t))
        """
        return self._format.reader.read_tile(tile_region, c=c, z=z, t=t)

    def window(self, viewport, out_width, out_height, c=None, z=None, t=None):
        """
        Get window for specified viewport. The output dimensions are best-effort i.e.
        out_width and out_height are the effective spatial lengths if the underlying window
        extractor is able to return these spatial dimensions.

        Returns
        -------
        window: image-like (PILImage, VIPSImage, numpy array)
            The window (dimensions: try_out_width x try_out_height x len(c) x len(z) x len(t))
        """
        if hasattr(self._format.reader, "read_window"):
            return self._format.reader.read_window(viewport, out_width, out_height, c=c, z=z, t=t)
        else:
            # TODO: implement window from tiles
            raise NotImplementedError

    def thumbnail(self, out_width, out_height, precomputed=False, c=None, z=None, t=None):
        """
        Get thumbnail. The output dimensions are best-effort i.e. out_width and out_height
        are the effective spatial lengths if the underlying thumbnail
        extractor is able to return these spatial dimensions.

        Returns
        -------
        thumbnail: image-like (PILImage, VIPSImage, numpy array)
            The thumbnail (dimensions: try_out_width x try_out_height x len(c) x len(z) x len(t))
        """
        if hasattr(self._format.reader, "read_thumb"):
            return self._format.reader.read_thumb(out_width, out_height, precomputed=precomputed, c=c, z=z, t=t)
        else:
            # TODO
            raise NotImplementedError

    def label(self, out_width, out_height):
        """
        Get associated image "label". The output dimensions are best-effort.
        """
        if self.associated_label.exists and hasattr(self._format.reader, "read_label"):
            return self._format.reader.read_label(out_width, out_height)
        else:
            return None

    def macro(self, out_width, out_height):
        """
        Get associated image "macro". The output dimensions are best-effort.
        """
        if self.associated_macro.exists and hasattr(self._format.reader, "read_macro"):
            return self._format.reader.read_macro(out_width, out_height)
        else:
            return None
