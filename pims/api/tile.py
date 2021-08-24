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
from typing import Optional

from fastapi import APIRouter, Depends, Query, Path as PathParam

from pims.api.exceptions import check_representation_existence, \
    BadRequestException
from pims.api.utils.header import add_image_size_limit_header, ImageRequestHeaders, SafeMode
from pims.api.utils.image_parameter import check_tileindex_validity, check_tilecoord_validity, \
    safeguard_output_dimensions, ensure_list, get_channel_indexes, check_reduction_validity, get_zslice_indexes, \
    get_timepoint_indexes, check_array_size, parse_intensity_bounds, parse_filter_ids, parse_colormap_ids
from pims.api.utils.mimetype import get_output_format, VISUALISATION_MIMETYPES, OutputExtension, \
    extension_path_parameter
from pims.api.utils.models import Colorspace, TierIndexType, TileRequest, TargetZoomTileIndex, \
    TargetZoomTileCoordinates, ImageOpsDisplayQueryParams, TargetZoom, \
    TileX, TileY, TileIndex, TargetLevel, PlaneSelectionQueryParams
from pims.api.utils.parameter import imagepath_parameter
from pims.config import get_settings, Settings
from pims.files.file import Path
from pims.filters import FILTERS
from pims.processing.colormaps import ALL_COLORMAPS
from pims.processing.image_response import TileResponse, WindowResponse

router = APIRouter()
tile_tags = ['Tiles']
norm_tile_tags = ['Normalized tiles']


@router.post('/image/{filepath:path}/tile{extension:path}', tags=tile_tags)
def show_tile_with_body(
        body: TileRequest,
        path: Path = Depends(imagepath_parameter),
        extension: OutputExtension = Depends(extension_path_parameter),
        headers: ImageRequestHeaders = Depends(),
        config: Settings = Depends(get_settings)
):
    """
    **`GET with body` - when a GET with URL encoded query parameters is not possible due to URL size limits, a POST
    with body content must be used.**

    Get a 8-bit tile optimized for visualisation, with given channels, focal
    planes and timepoints. If multiple channels are given (slice or selection), they are merged. If multiple focal
    planes or timepoints are given (slice or selection), a reduction function must be provided.

    **By default**, all image channels are used and when the image is multidimensional, the
     tile is extracted from the median focal plane at first timepoint.
    """
    return _show_tile(path, **body.dict(), normalized=False,
                      extension=extension, headers=headers, config=config)


@router.post('/image/{filepath:path}/normalized-tile{extension:path}', tags=norm_tile_tags)
def show_tile_with_body(
        body: TileRequest,
        path: Path = Depends(imagepath_parameter),
        extension: OutputExtension = Depends(extension_path_parameter),
        headers: ImageRequestHeaders = Depends(),
        config: Settings = Depends(get_settings)
):
    """
    **`GET with body` - when a GET with URL encoded query parameters is not possible due to URL size limits, a POST
    with body content must be used.**

    Get a 8-bit normalized tile optimized for visualisation, with given channels, focal
    planes and timepoints. If multiple channels are given (slice or selection), they are merged. If multiple focal
    planes or timepoints are given (slice or selection), a reduction function must be provided.

    **By default**, all image channels are used and when the image is multidimensional, the
     tile is extracted from the median focal plane at first timepoint.
    """
    return _show_tile(path, **body.dict(), normalized=True,
                      extension=extension, headers=headers, config=config)


def _show_tile(
        path: Path,
        normalized: bool,
        tile: dict,
        channels, z_slices, timepoints,
        min_intensities, max_intensities, filters, gammas, log,
        extension, headers, config,
        colormaps=None, c_reduction="ADD", z_reduction=None, t_reduction=None
):
    in_image = path.get_spatial()
    check_representation_existence(in_image)

    if not normalized or in_image.is_pyramid_normalized:
        pyramid = in_image.pyramid
        is_window = False
    else:
        pyramid = in_image.normalized_pyramid
        is_window = True

    if 'zoom' in tile:
        reference_tier_index = tile['zoom']
        tier_index_type = TierIndexType.ZOOM
    else:
        reference_tier_index = tile['level']
        tier_index_type = TierIndexType.LEVEL

    if 'ti' in tile:
        check_tileindex_validity(pyramid, tile['ti'],
                                 reference_tier_index, tier_index_type)
        tile_region = pyramid.get_tier_at(
            reference_tier_index, tier_index_type).ti2region(tile['ti'])
    else:
        check_tilecoord_validity(pyramid, tile['tx'], tile['ty'],
                                 reference_tier_index, tier_index_type)
        tile_region = pyramid.get_tier_at(
            reference_tier_index, tier_index_type).txty2region(tile['tx'], tile['ty'])

    out_format, mimetype = get_output_format(extension, headers.accept, VISUALISATION_MIMETYPES)
    req_size = tile_region.width, tile_region.height
    out_size = safeguard_output_dimensions(headers.safe_mode, config.output_size_limit, *req_size)
    out_width, out_height = out_size

    channels = ensure_list(channels)
    z_slices = ensure_list(z_slices)
    timepoints = ensure_list(timepoints)

    channels = get_channel_indexes(in_image, channels)
    check_reduction_validity(channels, c_reduction, 'channels')
    z_slices = get_zslice_indexes(in_image, z_slices)
    check_reduction_validity(z_slices, z_reduction, 'z_slices')
    timepoints = get_timepoint_indexes(in_image, timepoints)
    check_reduction_validity(timepoints, t_reduction, 'timepoints')

    min_intensities = ensure_list(min_intensities)
    max_intensities = ensure_list(max_intensities)
    colormaps = ensure_list(colormaps)
    filters = ensure_list(filters)
    gammas = ensure_list(gammas)

    array_parameters = (min_intensities, max_intensities, colormaps)
    for array_parameter in array_parameters:
        check_array_size(array_parameter, allowed=[0, 1, len(channels)], nullable=False)
    intensities = parse_intensity_bounds(in_image, channels, z_slices, timepoints, min_intensities, max_intensities)
    min_intensities, max_intensities = intensities
    colormaps = parse_colormap_ids(colormaps, ALL_COLORMAPS, channels, in_image.channels)

    array_parameters = (gammas, filters)
    for array_parameter in array_parameters:
        # Currently, we only allow 1 parameter to be applied to all channels
        check_array_size(array_parameter, allowed=[0, 1], nullable=False)
    filters = parse_filter_ids(filters, FILTERS)

    if is_window:
        tile = WindowResponse(
            in_image, channels, z_slices, timepoints,
            tile_region, out_format, out_width, out_height,
            c_reduction, z_reduction, t_reduction,
            gammas, filters, colormaps, min_intensities, max_intensities, log,
            8, Colorspace.AUTO)
    else:
        tile = TileResponse(
            in_image, channels, z_slices, timepoints,
            tile_region, out_format, out_width, out_height,
            c_reduction, z_reduction, t_reduction,
            gammas, filters, colormaps, min_intensities, max_intensities, log)

    return tile.http_response(
        mimetype,
        extra_headers=add_image_size_limit_header(dict(), *req_size, *out_size)
    )


def zoom_query_parameter(
        zoom: int = PathParam(...)
):
    return TargetZoom(__root__=zoom).dict()['__root__']


def level_query_parameter(
        level: int = PathParam(...)
):
    return TargetLevel(__root__=level).dict()['__root__']


def ti_query_parameter(
        ti: int = PathParam(...)
):
    return TileIndex(__root__=ti).dict()['__root__']


@router.get('/image/{filepath:path}/tile/zoom/{zoom:int}/ti/{ti:int}{extension:path}', tags=tile_tags)
def show_tile_by_zoom(
        path: Path = Depends(imagepath_parameter),
        zoom: int = Depends(zoom_query_parameter),
        ti: int = Depends(ti_query_parameter),
        extension: OutputExtension = Depends(extension_path_parameter),
        planes: PlaneSelectionQueryParams = Depends(),
        ops: ImageOpsDisplayQueryParams = Depends(),
        headers: ImageRequestHeaders = Depends(),
        config: Settings = Depends(get_settings),
):
    """
    Get a 8-bit tile at a given zoom level and tile index, optimized for visualisation, with given channels, focal
    planes and timepoints. If multiple channels are given (slice or selection), they are merged. If multiple focal
    planes or timepoints are given (slice or selection), a reduction function must be provided.

    **By default**, all image channels are used and when the image is multidimensional, the
    tile is extracted from the median focal plane at first timepoint.
    """
    tile = dict(zoom=zoom, ti=ti)
    return _show_tile(path, False, tile, **planes.dict(), **ops.dict(),
                      extension=extension, headers=headers, config=config)


@router.get('/image/{filepath:path}/tile/level/{level:int}/ti/{ti:int}{extension:path}', tags=tile_tags)
def show_tile_by_level(
        path: Path = Depends(imagepath_parameter),
        level: int = Depends(level_query_parameter),
        ti: int = Depends(ti_query_parameter),
        extension: OutputExtension = Depends(extension_path_parameter),
        planes: PlaneSelectionQueryParams = Depends(),
        ops: ImageOpsDisplayQueryParams = Depends(),
        headers: ImageRequestHeaders = Depends(),
        config: Settings = Depends(get_settings),
):
    """
    Get a 8-bit tile at a given zoom level and tile index, optimized for visualisation, with given channels, focal
    planes and timepoints. If multiple channels are given (slice or selection), they are merged. If multiple focal
    planes or timepoints are given (slice or selection), a reduction function must be provided.

    **By default**, all image channels are used and when the image is multidimensional, the
     tile is extracted from the median focal plane at first timepoint.
    """
    tile = dict(level=level, ti=ti)
    return _show_tile(path, False, tile, **planes.dict(), **ops.dict(),
                      extension=extension, headers=headers, config=config)


@router.get('/image/{filepath:path}/normalized-tile/zoom/{zoom:int}/ti/{ti:int}{extension:path}', tags=norm_tile_tags)
def show_normalized_tile_by_zoom(
        path: Path = Depends(imagepath_parameter),
        zoom: int = Depends(zoom_query_parameter),
        ti: int = Depends(ti_query_parameter),
        extension: OutputExtension = Depends(extension_path_parameter),
        planes: PlaneSelectionQueryParams = Depends(),
        ops: ImageOpsDisplayQueryParams = Depends(),
        headers: ImageRequestHeaders = Depends(),
        config: Settings = Depends(get_settings),
):
    """
    Get a 8-bit normalized tile at a given zoom level and tile index, optimized for visualisation, with given channels,
    focal planes and timepoints. If multiple channels are given (slice or selection), they are merged. If multiple focal
    planes or timepoints are given (slice or selection), a reduction function must be provided.

    **By default**, all image channels are used and when the image is multidimensional, the
    tile is extracted from the median focal plane at first timepoint.
    """
    tile = dict(zoom=zoom, ti=ti)
    return _show_tile(path, True, tile, **planes.dict(), **ops.dict(),
                      extension=extension, headers=headers, config=config)


@router.get('/image/{filepath:path}/normalized-tile/level/{level:int}/ti/{ti:int}{extension:path}', tags=norm_tile_tags)
def show_normalized_tile_by_level(
        path: Path = Depends(imagepath_parameter),
        level: int = Depends(level_query_parameter),
        ti: int = Depends(ti_query_parameter),
        extension: OutputExtension = Depends(extension_path_parameter),
        planes: PlaneSelectionQueryParams = Depends(),
        ops: ImageOpsDisplayQueryParams = Depends(),
        headers: ImageRequestHeaders = Depends(),
        config: Settings = Depends(get_settings),
):
    """
    Get a 8-bit normalized tile at a given zoom level and tile index, optimized for visualisation, with given channels, 
    focal planes and timepoints. If multiple channels are given (slice or selection), they are merged. If multiple focal
    planes or timepoints are given (slice or selection), a reduction function must be provided.

    **By default**, all image channels are used and when the image is multidimensional, the
     tile is extracted from the median focal plane at first timepoint.
    """
    tile = dict(level=level, ti=ti)
    return _show_tile(path, True, tile, **planes.dict(), **ops.dict(),
                      extension=extension, headers=headers, config=config)


@router.get('/image/tile.jpg', tags=norm_tile_tags, deprecated=True)
def show_tile_v1(
        zoomify: str,
        x: int,
        y: int,
        z: int,
        ops: ImageOpsDisplayQueryParams = Depends(),
        mime_type: Optional[str] = Query(None, alias='mimeType'),
        tile_group: Optional[str] = Query(None, alias='tileGroup'),
        config: Settings = Depends(get_settings)
):
    """
    Get a tile using IMS V1.x specification.
    """
    zoom = TargetZoom(__root__=z)
    tx, ty = TileX(__root__=x), TileY(__root__=y)
    tile = TargetZoomTileCoordinates(zoom=zoom, tx=tx, ty=ty)
    return _show_tile(
        imagepath_parameter(zoomify),
        normalized=True,
        tile=tile.dict(),
        channels=None, z_slices=None, timepoints=None,
        **ops.dict(),
        extension=OutputExtension.JPEG,
        headers=ImageRequestHeaders("image/jpeg", SafeMode.SAFE_RESIZE),
        config=config
    )


@router.get('/slice/tile', tags=norm_tile_tags, deprecated=True)
def show_tile_v2(
        z: int,
        fif: Optional[str] = None,
        zoomify: Optional[str] = None,
        x: Optional[int] = None,
        y: Optional[int] = None,
        tile_index: Optional[int] = Query(None, alias='tileIndex'),
        ops: ImageOpsDisplayQueryParams = Depends(),
        tile_group: Optional[str] = Query(None, alias='tileGroup'),
        mime_type: str = Query(None, alias='mimeType'),
        config: Settings = Depends(get_settings)
):
    """
    Get a tile using IMS V2.x specification.
    """
    zoom = TargetZoom(__root__=z)
    if all(i is not None for i in (zoomify, tile_group, x, y)):
        tx, ty = TileX(__root__=x), TileY(__root__=y)
        tile = TargetZoomTileCoordinates(zoom=zoom, tx=tx, ty=ty)
        path = imagepath_parameter(zoomify)
    elif all(i is not None for i in (fif, z, tile_index)):
        ti = TileIndex(__root__=tile_index)
        tile = TargetZoomTileIndex(zoom=zoom, ti=ti),
        path = imagepath_parameter(fif)
    else:
        raise BadRequestException(detail="Incoherent set of parameters.")

    return _show_tile(
        path,
        normalized=True,
        tile=tile.dict(),
        channels=None, z_slices=None, timepoints=None,
        **ops.dict(),
        extension=OutputExtension.JPEG,
        headers=ImageRequestHeaders("image/jpeg", SafeMode.SAFE_RESIZE),
        config=config
    )
