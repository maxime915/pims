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

import shutil
from abc import ABC
from functools import cached_property

import numpy as np
import zarr as zarr
from skimage.exposure import histogram
from zarr.errors import _BaseZarrError as ZarrError

from pims.api.exceptions import NoMatchingFormatProblem
from pims.api.utils.models import HistogramType
from pims.api.utils.output_parameter import get_thumb_output_dimensions
from pims.files.file import Path
from pims.formats.utils.histogram import HistogramReaderInterface
from pims.processing.adapters import imglib_adapters

ZHF_PER_PLANE = "plane"
ZHF_PER_CHANNEL = "channel"
ZHF_PER_IMAGE = "image"
ZHF_HIST = "hist"
ZHF_BOUNDS = "bounds"
ZHF_ATTR_TYPE = "histogram_type"
ZHF_ATTR_FORMAT = "histogram_format"


class HistogramFormat(HistogramReaderInterface, ABC):
    def __init__(self, path, **kwargs):
        self.path = path

    @classmethod
    def match(cls, path, *args, **kwargs):
        return False


class ZarrHistogramFormat(HistogramFormat):
    def __init__(self, path, **kwargs):
        super().__init__(path)
        self.__dict__.update(kwargs)

        if not hasattr(self, 'zhf'):
            self.zhf = zarr.open(str(self.path), mode='r')

    @classmethod
    def match(cls, path, *args, **kwargs):
        try:
            zhf = zarr.open(str(path), mode='r')
            if ZHF_ATTR_FORMAT in zhf.attrs:
                return cls(path, zhf=zhf)
        except ZarrError:
            return False

    @cached_property
    def per_planes(self):
        return ZHF_PER_PLANE in self.zhf

    @cached_property
    def per_channels(self):
        return ZHF_PER_CHANNEL in self.zhf

    @cached_property
    def per_image(self):
        return ZHF_PER_IMAGE in self.zhf

    def type(self):
        return self.zhf.attrs[ZHF_ATTR_TYPE]

    def image_bounds(self):
        return tuple(self.zhf[f"{ZHF_PER_IMAGE}/{ZHF_BOUNDS}"])

    def image_histogram(self):
        return self.zhf[f"{ZHF_PER_IMAGE}/{ZHF_HIST}"][:]

    def channels_bounds(self):
        if not self.per_channels:
            return [self.image_bounds()]
        return list(map(tuple, self.zhf[f"{ZHF_PER_CHANNEL}/{ZHF_BOUNDS}"]))

    def channel_bounds(self, c):
        if not self.per_channels:
            return self.image_bounds()
        return tuple(self.zhf[f"{ZHF_PER_CHANNEL}/{ZHF_BOUNDS}"][c])

    def channel_histogram(self, c):
        if not self.per_channels:
            return self.image_histogram()

        if type(c) is list:
            return self.zhf[f"{ZHF_PER_CHANNEL}/{ZHF_HIST}"].get_orthogonal_selection((c,))
        return self.zhf[f"{ZHF_PER_CHANNEL}/{ZHF_HIST}"][c]

    def planes_bounds(self):
        if not self.per_planes:
            return self.channels_bounds()
        return list(map(tuple, self.zhf[f"{ZHF_PER_PLANE}/{ZHF_BOUNDS}"].reshape((-1, 2))))

    def plane_bounds(self, c, z, t):
        if not self.per_planes:
            return self.channel_bounds(c)
        return tuple(self.zhf[f"{ZHF_PER_PLANE}/{ZHF_BOUNDS}"][t, z, c])

    def plane_histogram(self, c, z, t):
        if not self.per_planes:
            return self.channel_histogram(c)

        if type(c) is list or type(z) is list or type(t) is list:
            c = c if type(c) is list else [c]
            z = z if type(z) is list else [z]
            t = t if type(t) is list else [t]
            return self.zhf[f"{ZHF_PER_PLANE}/{ZHF_HIST}"].get_orthogonal_selection((t, z, c))

        return self.zhf[f"{ZHF_PER_PLANE}/{ZHF_HIST}"][t, z, c]


HISTOGRAM_FORMATS = [ZarrHistogramFormat]


class Histogram(Path, HistogramReaderInterface):
    def __init__(self, *pathsegments, format=None):
        super().__init__(*pathsegments)

        _format = None
        if format:
            _format = format
        else:
            for possible_format in HISTOGRAM_FORMATS:
                _format = possible_format.match(self)
                if _format is not None:
                    break

        if _format is None:
            raise NoMatchingFormatProblem(self)
        else:
            self._format = _format

    def type(self) -> HistogramType:
        return self._format.type()

    def image_bounds(self):
        return self._format.image_bounds()

    def image_histogram(self):
        return self._format.image_histogram()

    def channels_bounds(self):
        return self._format.channels_bounds()

    def channel_bounds(self, c):
        return self._format.channel_bounds(c)

    def channel_histogram(self, c):
        return self._format.channel_histogram(c)

    def planes_bounds(self):
        return self._format.planes_bounds()

    def plane_bounds(self, c, z, t):
        return self._format.plane_bounds(c, z, t)

    def plane_histogram(self, c, z, t):
        return self._format.plane_histogram(c, z, t)


MAX_PIXELS_COMPLETE_HISTOGRAM = 1024 * 1024


def _extract_np_thumb(image):
    tw, th = get_thumb_output_dimensions(image, length=1024, allow_upscaling=False)
    ratio = image.n_pixels / (tw * th)

    def channels_for_read(read, in_image):
        first = read * in_image.n_channels_per_read
        last = min(in_image.n_channels, first + in_image.n_channels_per_read)
        return range(first, last)

    n_c_reads = int(np.ceil(image.n_channels / image.n_channels_per_read))
    for t in range(image.duration):
        for z in range(image.depth):
            for c_read in range(n_c_reads):
                c_range = channels_for_read(c_read, image)
                c = c_range[0]  # TODO
                thumb = image.thumbnail(tw, th, precomputed=False, c=c, t=t, z=z)
                npthumb = imglib_adapters.get((type(thumb), np.ndarray))(thumb)
                npthumb = np.atleast_3d(npthumb)
                if npthumb.shape[2] != len(c_range):
                    # TODO: improve palette support! !! if we get more channels than expected,
                    #  we have a color palette image For now, try to discard the palette by only
                    #  keeping the expected channel in the response
                    mod_range = [c % npthumb.shape[2] for c in c_range]
                    npthumb = npthumb[:, :, mod_range]
                yield npthumb, c_range, z, t, ratio


def argmin_nonzero(arr, axis=-1):
    return np.argmax(arr != 0, axis=axis)


def argmax_nonzero(arr, axis=-1):
    return arr.shape[axis] - np.argmax(np.flip(arr, axis=axis) != 0, axis=axis) - 1


def clamp_histogram(hist, bounds=None):
    if bounds is None:
        inf = argmin_nonzero(hist)
        sup = argmax_nonzero(hist)
    else:
        inf, sup = bounds
    return hist[inf:sup + 1], np.arange(inf, sup + 1)


def build_histogram_file(
    in_image, dest, hist_type: HistogramType,
    overwrite: bool = False
):
    """
    Build an histogram for an image and save it as zarr file.
    Parameters
    ----------
    in_image : Image
        The image from which histogram has to be extracted.
    dest : Path
        The path where the histogram file will be saved.
    hist_type : HistogramType
        The type of histogram to build (FAST or COMPLETE)
    overwrite : bool (default: False)
        Whether overwrite existing histogram file at `dest` if any

    Returns
    -------
    histogram : Histogram
        The zarr histogram file in read-only mode
    """
    n_values = 2 ** in_image.significant_bits

    if in_image.n_pixels < MAX_PIXELS_COMPLETE_HISTOGRAM:
        extract_fn = _extract_np_thumb
        hist_type = HistogramType.COMPLETE
    else:
        if hist_type == HistogramType.FAST:
            extract_fn = _extract_np_thumb
        else:
            extract_fn = in_image.tile
            raise NotImplementedError()  # TODO

    if not overwrite and dest.exists():
        raise FileExistsError(dest)

    # While the file is not fully built, we save it at a temporary location
    tmp_dest = dest.parent / Path(f"tmp_{dest.name}")
    zroot = zarr.open_group(str(tmp_dest), mode='w')
    zroot.attrs[ZHF_ATTR_TYPE] = hist_type
    zroot.attrs[ZHF_ATTR_FORMAT] = "PIMS-1.0"

    # Create the group for plane histogram
    # TODO: usa Dask to manipulate Zarr arrays (for bounds)
    #  so that we can fill the zarr array incrementally
    # https://github.com/zarr-developers/zarr-python/issues/446
    shape = (in_image.duration, in_image.depth, in_image.n_channels)
    zplane = zroot.create_group(ZHF_PER_PLANE)
    npplane_hist = np.zeros(shape=shape + (n_values,), dtype=np.uint64)
    for data, c_range, z, t, ratio in extract_fn(in_image):
        for read, c in enumerate(c_range):
            h, _ = histogram(data[:, :, read], source_range='dtype')
            npplane_hist[t, z, c, :] += np.rint(h * ratio).astype(np.uint64)
    zplane.array(ZHF_HIST, npplane_hist)
    zplane.array(
        ZHF_BOUNDS,
        np.stack(
            (argmin_nonzero(npplane_hist),
             argmax_nonzero(npplane_hist)), axis=-1
        )
    )

    # Create the group for channel histogram
    zchannel = zroot.create_group(ZHF_PER_CHANNEL)
    npchannel_hist = np.sum(npplane_hist, axis=(0, 1))
    zchannel.array(ZHF_HIST, npchannel_hist)
    zchannel.array(
        ZHF_BOUNDS,
        np.stack(
            (argmin_nonzero(npchannel_hist),
             argmax_nonzero(npchannel_hist)), axis=-1
        )
    )

    # Create the group for image histogram
    zimage = zroot.create_group(ZHF_PER_IMAGE)
    npimage_hist = np.sum(npchannel_hist, axis=0)
    zimage.array(ZHF_HIST, npimage_hist)
    zimage.array(
        ZHF_BOUNDS,
        [argmin_nonzero(npimage_hist), argmax_nonzero(npimage_hist)]
    )

    # Remove redundant data
    if in_image.duration == 1 and in_image.depth == 1:
        del zroot[ZHF_PER_PLANE]
        if in_image.n_channels == 1:
            del zroot[ZHF_PER_CHANNEL]

    # Move the zarr file (directory) to final location
    if overwrite and dest.exists():
        shutil.rmtree(dest)
    tmp_dest.replace(dest)
    return Histogram(dest, format=ZarrHistogramFormat)
