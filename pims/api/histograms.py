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

from fastapi import APIRouter, Depends, Query, Body
from pydantic import conint, BaseModel, Field

from pims.api.exceptions import check_representation_existence
from pims.api.utils.image_parameter import ensure_list, get_channel_indexes, get_zslice_indexes, get_timepoint_indexes
from pims.api.utils.models import HistogramType, CollectionSize
from pims.api.utils.parameter import imagepath_parameter
from pims.api.utils.response import response_list
from pims.files.file import Path

router = APIRouter()
api_tags = ['Histograms']


class Histogram(BaseModel):
    type: HistogramType = Field(...)
    minimum: int = Field(..., description="Minimum intensity value")
    maximum: int = Field(..., description="Maximum intensity value")
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


@router.get('/image/{filepath:path}/histogram/per-image', tags=api_tags, response_model=Histogram)
def show_image_histogram(
        path: Path = Depends(imagepath_parameter)
):
    """
    Get histogram for full image where all planes (C,Z,T) are merged.
    """
    in_image = path.get_spatial()
    check_representation_existence(in_image)

    mini, maxi = in_image.image_bounds()
    hist = list(in_image.image_histogram())
    htype = in_image.histogram_type()
    return Histogram(minimum=mini, maximum=maxi, histogram=hist, type=htype)


@router.get('/image/{filepath:path}/histogram/per-channels', tags=api_tags, response_model=ChannelsHistogramCollection)
def show_channels_histogram(
        path: Path = Depends(imagepath_parameter),
        channels: Optional[List[conint(ge=0)]] = Query(None, description="Only return histograms for these channels")
):
    """
    Get histograms per channel where all planes (Z,T) are merged.
    """
    in_image = path.get_spatial()
    check_representation_existence(in_image)

    channels = ensure_list(channels)
    channels = get_channel_indexes(in_image, channels)

    histograms = []
    htype = in_image.histogram_type()
    for channel in channels:
        mini, maxi = in_image.channel_bounds(channel)
        hist = list(in_image.channel_histogram(channel))
        histograms.append(ChannelHistogram(channel=channel, minimum=mini, maximum=maxi, histogram=hist, type=htype))

    return response_list(histograms)


@router.get('/image/{filepath:path}/histogram/per-plane/c/{channels}/z/{z_slices}/t/{timepoints}', tags=api_tags,
            response_model=PlaneHistogramCollection)
def show_plane_histogram(
        channels: conint(ge=0),
        z_slices: conint(ge=0),
        timepoints: conint(ge=0),
        path: Path = Depends(imagepath_parameter),
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
    htype = in_image.histogram_type()
    for c, z, t in itertools.product(channels, z_slices, timepoints):
        mini, maxi = in_image.plane_bounds(c, z, t)
        hist = list(in_image.plane_histogram(c, z, t))
        histograms.append(
            PlaneHistogram(channel=c, z_slice=z, timepoint=t,
                           minimum=mini, maximum=maxi,
                           histogram=hist, type=htype)
        )

    return response_list(histograms)


@router.post('/image/{filepath:path}/histogram', tags=api_tags)
def compute_histogram(
        path: Path = Depends(imagepath_parameter),
        companion_file_id: Optional[int] = Body(None, description="Cytomine ID for the histogram")
):
    """
    Ask for histogram computation
    """
    pass
