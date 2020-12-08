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

from pims.api.exceptions import NoMatchingFormatProblem
from pims.files.file import Path


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
        return self._format.get_image_metadata().width

    @property
    def physical_size_x(self):
        return self._format.get_image_metadata(True).physical_size_x

    @property
    def height(self):
        return self._format.get_image_metadata().height

    @property
    def physical_size_y(self):
        return self._format.get_image_metadata(True).physical_size_y

    @property
    def depth(self):
        return self._format.get_image_metadata().depth

    @property
    def physical_size_z(self):
        return self._format.get_image_metadata(True).physical_size_z

    @property
    def duration(self):
        return self._format.get_image_metadata().duration

    @property
    def frame_rate(self):
        return self._format.get_image_metadata().frame_rate

    @property
    def n_channels(self):
        return self._format.get_image_metadata().n_channels

    @property
    def pixel_type(self):
        return self._format.get_image_metadata().pixel_type

    @property
    def significant_bits(self):
        return self._format.get_image_metadata().significant_bits

    @property
    def acquisition_datetime(self):
        return self._format.get_image_metadata(True).acquisition_datetime

    @property
    def description(self):
        return self._format.get_image_metadata(True).description

    @property
    def channels(self):
        return self._format.get_image_metadata(True).channels

    @property
    def objective(self):
        return self._format.get_image_metadata(True).objective

    @property
    def microscope(self):
        return self._format.get_image_metadata(True).microscope

    @property
    def associated_thumb(self):
        return self._format.get_image_metadata(True).associated_thumb
    
    @property
    def associated_label(self):
        return self._format.get_image_metadata(True).associated_label
    
    @property
    def associated_macro(self):
        return self._format.get_image_metadata(True).associated_macro

    @property
    def raw_metadata(self):
        return self._format.get_raw_metadata()

    @property
    def pyramid(self):
        try:
            return self._format.pyramid
        except AttributeError:
            return None

    def tile(self, level, tile_index, c=None, z=None, t=None):
        """
        Get tile at specified level and tile index for all (C,Z,T) combinations.

        Returns
        ------
        tile: image-like (PILImage, VIPSImage, numpy array)
            The tile (dimensions: tile_size x tile_size x len(c) x len(z) x len(t))
        """
        return self._format.get_tile(level, tile_index, c, z, t)

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
        if hasattr(self._format, "get_window"):
            return self._format.get_window(viewport, out_width, out_height, c, z, t)
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
        if hasattr(self._format, "read_thumbnail"):
            return self._format.read_thumbnail(out_width, out_height, precomputed, c, z, t)
        else:
            # TODO
            raise NotImplementedError

    def label(self, out_width, out_height):
        """
        Get associated image "label". The output dimensions are best-effort.
        """
        if self.associated_label.exists and hasattr(self._format, "read_label"):
            return self._format.read_label(out_width, out_height)
        else:
            return None

    def macro(self, out_width, out_height):
        """
        Get associated image "macro". The output dimensions are best-effort.
        """
        if self.associated_macro.exists and hasattr(self._format, "read_macro"):
            return self._format.read_macro(out_width, out_height)
        else:
            return None
