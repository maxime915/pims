from functools import cached_property
from typing import Optional

import zarr as zarr

from pims.formats.utils.abstract import AbstractHistogramReader

ZHF_PER_PLANE = "plane"
ZHF_PER_CHANNEL = "channel"
ZHF_PER_IMAGE = "image"
ZHF_HIST = "hist"
ZHF_BOUNDS = "bounds"


def cached_zarr_histogram(format) -> Optional[zarr.Group]:
    def _open(image_path):
        hist_path = image_path.get_histogram()
        if hist_path:
            return zarr.open(hist_path, mode='r')
        return None
    return format.get_cached('_zh', _open, format.path)


class ZarrHistogramReader(AbstractHistogramReader):

    @property
    def zhf(self):
        return cached_zarr_histogram(self.format)

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
        if not self.zhf:
            return super().type()
        return self.zhf.attrs["type"]

    def image_bounds(self):
        if not self.zhf:
            return super().image_bounds()
        return tuple(self.zhf[f"{ZHF_PER_IMAGE}/{ZHF_BOUNDS}"])

    def image_histogram(self):
        if not self.zhf:
            return super().image_histogram()
        return self.zhf[f"{ZHF_PER_IMAGE}/{ZHF_HIST}"][:]

    def channels_bounds(self):
        if not self.zhf:
            return super().channels_bounds()
        if not self.per_channels:
            return [self.image_bounds()]
        return list(map(tuple, self.zhf[f"{ZHF_PER_CHANNEL}/{ZHF_BOUNDS}"]))

    def channel_bounds(self, c):
        if not self.zhf:
            return super().channel_bounds(c)
        if not self.per_channels:
            return self.image_bounds()
        return tuple(self.zhf[f"{ZHF_PER_CHANNEL}/{ZHF_BOUNDS}"][c])

    def channel_histogram(self, c):
        if not self.zhf:
            return super().channel_histogram(c)
        if not self.per_channels:
            return self.image_histogram()
        return self.zhf[f"{ZHF_PER_IMAGE}/{ZHF_HIST}"][c]

    def planes_bounds(self):
        if not self.zhf:
            return super().planes_bounds()
        if not self.per_planes:
            return self.channels_bounds()
        return list(map(tuple, self.zhf[f"{ZHF_PER_PLANE}/{ZHF_BOUNDS}"].reshape((-1, 2))))

    def plane_bounds(self, c, z, t):
        if not self.zhf:
            return super().plane_bounds(c, z, t)
        if not self.per_planes:
            return self.channel_bounds(c)
        return tuple(self.zhf[f"{ZHF_PER_PLANE}/{ZHF_BOUNDS}"][t, z, c])

    def plane_histogram(self, c, z, t):
        if not self.zhf:
            return super().plane_histogram(c, z, t)
        if not self.per_planes:
            return self.channel_histogram(c)
        return self.zhf[f"{ZHF_PER_PLANE}/{ZHF_HIST}"][t, z, c]

