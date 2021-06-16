from abc import ABC, abstractmethod
from functools import cached_property

from skimage.filters import threshold_otsu, threshold_isodata, threshold_yen, threshold_li, threshold_minimum

from pims.api.utils.models import FilterType, Colorspace
from pims.files.histogram import clamp_histogram
from pims.filters import AbstractFilter

from pyvips import Image as VIPSImage


class AbstractGlobalFilter(AbstractFilter, ABC):
    @classmethod
    def get_type(cls):
        return FilterType.GLOBAL


class AbstractGlobalThresholdFilter(AbstractGlobalFilter, ABC):
    @classmethod
    def require_histogram(cls):
        return True

    @classmethod
    def required_colorspace(cls):
        return Colorspace.GRAY

    def __init__(self, histogram=None, white_objects=False):
        super().__init__(histogram)
        self.white_objects = white_objects
        self._impl[VIPSImage] = self._vips_impl

    @cached_property
    @abstractmethod
    def threshold(self):
        pass

    def _vips_impl(self, img, *args, **kwargs):
        if self.white_objects:
            return img <= self.threshold
        else:
            return img > self.threshold


class OtsuFilter(AbstractGlobalThresholdFilter):
    @classmethod
    def get_description(cls):
        return "Otsu global filtering"

    @cached_property
    def threshold(self):
        return threshold_otsu(hist=clamp_histogram(self.histogram))


class IsodataFilter(AbstractGlobalThresholdFilter):
    @cached_property
    def threshold(self):
        return threshold_isodata(hist=clamp_histogram(self.histogram))

    @classmethod
    def get_description(cls):
        return "Isodata global filtering"


class YenFilter(AbstractGlobalThresholdFilter):
    @cached_property
    def threshold(self):
        return threshold_yen(hist=clamp_histogram(self.histogram))

    @classmethod
    def get_description(cls):
        return "Yen global filtering"


class MinimumFilter(AbstractGlobalThresholdFilter):
    @cached_property
    def threshold(self):
        return threshold_minimum(hist=clamp_histogram(self.histogram))

    @classmethod
    def get_description(cls):
        return "Minimum global filtering"

