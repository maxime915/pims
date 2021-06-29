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
import itertools
from typing import Optional, List

from fastapi import APIRouter, Depends, Query, BackgroundTasks, Response
from pydantic import conint, BaseModel, Field
from starlette import status

from pims.api.exceptions import check_representation_existence, BadRequestException
from pims.api.utils.image_parameter import ensure_list, get_channel_indexes, get_zslice_indexes, get_timepoint_indexes
from pims.api.utils.models import HistogramType, CollectionSize
from pims.api.utils.parameter import imagepath_parameter
from pims.api.utils.response import response_list
from pims.files.file import Path, HISTOGRAM_STEM
from pims.files.histogram import build_histogram_file, argmin_nonzero, argmax_nonzero

router = APIRouter()
api_tags = ['Histograms']


class Histogram(BaseModel):
    type: HistogramType = Field(...)
    minimum: int = Field(..., description="Minimum intensity value")
    maximum: int = Field(..., description="Maximum intensity value")
    first_bin: int = Field(..., description="Index of first bin returned in histogram")
    last_bin: int = Field(..., description="Index of last bin returned in histogram")
    n_bins: int = Field(..., description="The number of bins in the full range histogram")
    histogram: List[int] = Field(..., description="Histogram")


class ChannelHistogram(Histogram):
    channel: int = Field(..., description="Image channel index")


class ChannelsHistogramCollection(CollectionSize):
    items: List[ChannelHistogram] = Field(None, description='Array of channel histograms', title='Channel histogram')


class PlaneHistogram(ChannelHistogram):
    z_slice: int = Field(..., description="Image focal point index")
    timepoint: int = Field(..., description="Image timepoint index")


class PlaneHistogramCollection(CollectionSize):
    items: List[PlaneHistogram] = Field(None, description='Array of plane histograms', title='Plane histogram')


def parse_n_bins(n_bins, hist_len):
    return n_bins if n_bins <= hist_len else hist_len


def _histogram_binning(hist, n_bins):
    if hist.shape[-1] % n_bins != 0:
        raise BadRequestException(
            detail=f"Cannot make {n_bins} bins from histogram "
            f"with shape {hist.shape}"
        )
    return hist.reshape((n_bins, -1)).sum(axis=1)


def histogram_formatter(hist, bounds, n_bins, full_range):
    if n_bins == len(hist):
        if not full_range:
            hist = hist[bounds[0]:bounds[1] + 1]
        return hist, bounds
    else:
        hist = _histogram_binning(hist, n_bins)
        bounds = argmin_nonzero(hist), argmax_nonzero(hist)
        if not full_range:
            hist = hist[bounds[0]:bounds[1] + 1]
        return hist, bounds


def is_power_of_2(n):
    return (n & (n - 1) == 0) and n != 0


class HistogramConfig:
    def __init__(
            self,
            n_bins: int = Query(
                256,
                description="Number of bins. Must be a power of 2. "
                            "If `nbins > 2 ** image.significant_bits` then "
                            "´nbins = 2 ** image.significant_bits` "
            ),
            full_range: bool = Query(
                False,
                description="Whether to return full histogram range, including leading and ending zero bins. "
                            "When set, `first_bin = 0` and `last_bin = 2 ** image.significant_bits - 1`.")
    ):
        if not is_power_of_2(n_bins):
            raise BadRequestException(detail=f"{n_bins} is not a power of 2.")

        self.n_bins = n_bins
        self.full_range = full_range


@router.get('/image/{filepath:path}/histogram/per-image',
            tags=api_tags, response_model=Histogram)
def show_image_histogram(
        path: Path = Depends(imagepath_parameter),
        hist_config: HistogramConfig = Depends()
):
    """
    Get histogram for full image where all planes (C,Z,T) are merged.
    """
    in_image = path.get_spatial()
    check_representation_existence(in_image)

    n_bins = parse_n_bins(hist_config.n_bins, len(in_image.value_range))
    htype = in_image.histogram_type()
    bounds = in_image.image_bounds()
    hist, bin_bounds = histogram_formatter(
        in_image.image_histogram(), bounds,
        n_bins, hist_config.full_range
    )
    mini, maxi = bounds
    first_bin, last_bin = bin_bounds
    return Histogram(
        minimum=mini, maximum=maxi, histogram=list(hist),
        type=htype, first_bin=first_bin, last_bin=last_bin, n_bins=n_bins
    )


@router.get('/image/{filepath:path}/histogram/per-channels',
            tags=api_tags, response_model=ChannelsHistogramCollection)
def show_channels_histogram(
        path: Path = Depends(imagepath_parameter),
        hist_config: HistogramConfig = Depends(),
        channels: Optional[List[conint(ge=0)]] = Query(None, description="Only return histograms for these channels"),
):
    """
    Get histograms per channel where all planes (Z,T) are merged.
    """
    in_image = path.get_spatial()
    check_representation_existence(in_image)

    channels = ensure_list(channels)
    channels = get_channel_indexes(in_image, channels)

    histograms = []
    n_bins = parse_n_bins(hist_config.n_bins, len(in_image.value_range))
    htype = in_image.histogram_type()
    for channel in channels:
        bounds = in_image.channel_bounds(channel)
        hist, bin_bounds = histogram_formatter(
            in_image.channel_histogram(channel), bounds,
            n_bins, hist_config.full_range
        )
        mini, maxi = bounds
        first_bin, last_bin = bin_bounds
        histograms.append(
            ChannelHistogram(
                channel=channel, minimum=mini, maximum=maxi,
                histogram=list(hist), type=htype,
                first_bin=first_bin, last_bin=last_bin, n_bins=n_bins
            )
        )

    return response_list(histograms)


@router.get('/image/{filepath:path}/histogram/per-plane/z/{z_slices}/t/{timepoints}',
            tags=api_tags, response_model=PlaneHistogramCollection)
def show_plane_histogram(
        z_slices: conint(ge=0),
        timepoints: conint(ge=0),
        path: Path = Depends(imagepath_parameter),
        hist_config: HistogramConfig = Depends(),
        channels: Optional[List[conint(ge=0)]] = Query(None, description="Only return histograms for these channels"),
):
    """
    Get histogram per plane.
    """
    in_image = path.get_spatial()
    check_representation_existence(in_image)

    channels = ensure_list(channels)
    z_slices = ensure_list(z_slices)
    timepoints = ensure_list(timepoints)

    channels = get_channel_indexes(in_image, channels)
    z_slices = get_zslice_indexes(in_image, z_slices)
    timepoints = get_timepoint_indexes(in_image, timepoints)

    histograms = []
    n_bins = parse_n_bins(hist_config.n_bins, len(in_image.value_range))
    htype = in_image.histogram_type()
    for c, z, t in itertools.product(channels, z_slices, timepoints):
        bounds = in_image.plane_bounds(c, z, t)
        hist, bin_bounds = histogram_formatter(
            in_image.plane_histogram(c, z, t), bounds,
            n_bins, hist_config.full_range
        )
        mini, maxi = bounds
        first_bin, last_bin = bin_bounds
        histograms.append(
            PlaneHistogram(channel=c, z_slice=z, timepoint=t,
                           minimum=mini, maximum=maxi,
                           histogram=list(hist), type=htype,
                           first_bin=first_bin, last_bin=last_bin,
                           n_bins=n_bins)
        )

    return response_list(histograms)


@router.post('/image/{filepath:path}/histogram', tags=api_tags)
def compute_histogram(
        response: Response,
        background: BackgroundTasks,
        path: Path = Depends(imagepath_parameter),
        # companion_file_id: Optional[int] = Body(None, description="Cytomine ID for the histogram")
        sync: bool = True,
        overwrite: bool = True
):
    """
    Ask for histogram computation
    """
    in_image = path.get_spatial()
    check_representation_existence(in_image)

    hist_type = HistogramType.FAST  # TODO: allow to build complete histograms
    hist_path = in_image.processed_root() / Path(HISTOGRAM_STEM)

    if sync:
        build_histogram_file(in_image, hist_path, hist_type, overwrite)
        response.status_code = status.HTTP_201_CREATED
    else:
        background.add_task(build_histogram_file, in_image, hist_path, hist_type, overwrite)
        response.status_code = status.HTTP_202_ACCEPTED
