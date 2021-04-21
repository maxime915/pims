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
from io import BytesIO

from connexion.exceptions import BadRequestProblem
from flask import request, current_app, send_file
from pims.api.exceptions import check_path_existence, check_path_is_single, check_representation_existence
from pims.api.utils.header import add_image_size_limit_header
from pims.api.utils.image_parameter import check_tileindex_validity, check_tilecoord_validity, \
    safeguard_output_dimensions, ensure_list, get_channel_indexes, check_reduction_validity, get_zslice_indexes, \
    get_timepoint_indexes, check_array_size, parse_intensity_bounds
from pims.api.utils.mimetype import get_output_format, VISUALISATION_MIMETYPES
from pims.api.utils.parameter import filepath2path
from pims.processing.image_response import TileResponse


def show_tile(filepath, zoom=None, level=None, ti=None, tx=None, ty=None,
              channels=None, z_slices=None, timepoints=None,
              c_reduction="ADD", z_reduction=None, t_reduction=None,
              min_intensities=None, max_intensities=None, colormaps=None, filters=None,
              gammas=None, log=None):
    path = filepath2path(filepath)
    check_path_existence(path)
    check_path_is_single(path)

    in_image = path.get_spatial()
    check_representation_existence(in_image)

    if zoom is not None:
        reference_tier_index = zoom
        tier_index_type = "ZOOM"
    elif level is not None:
        reference_tier_index = level
        tier_index_type = "LEVEL"
    else:
        raise BadRequestProblem(detail="Impossible to determine pyramid tier.")

    if ti is not None:
        check_tileindex_validity(in_image.pyramid, ti, reference_tier_index, tier_index_type)
        tile_region = in_image.pyramid.get_tier_at(reference_tier_index, tier_index_type).ti2region(ti)
    elif tx and ty is not None:
        check_tilecoord_validity(in_image.pyramid, tx, ty, reference_tier_index, tier_index_type)
        tile_region = in_image.pyramid.get_tier_at(reference_tier_index, tier_index_type).txty2region(tx, ty)
    else:
        # should not happen as this case is already handled by connexion.
        raise BadRequestProblem(detail="Impossible to determine tile position.")

    out_format, mimetype = get_output_format(request, VISUALISATION_MIMETYPES)
    safe_mode = request.headers.get('X-Image-Size-Safety', current_app.config['DEFAULT_IMAGE_SIZE_SAFETY_MODE'])
    out_width, out_height = safeguard_output_dimensions(safe_mode, current_app.config['OUTPUT_SIZE_LIMIT'],
                                                        tile_region.width, tile_region.height)

    channels, z_slices, timepoints = ensure_list(channels), ensure_list(z_slices), ensure_list(timepoints)
    min_intensities, max_intensities = ensure_list(min_intensities), ensure_list(max_intensities)
    colormaps, filters, gammas = ensure_list(colormaps), ensure_list(filters), ensure_list(gammas)

    channels = get_channel_indexes(in_image, channels)
    check_reduction_validity(channels, c_reduction, 'channels')
    z_slices = get_zslice_indexes(in_image, z_slices)
    check_reduction_validity(z_slices, z_reduction, 'z_slices')
    timepoints = get_timepoint_indexes(in_image, timepoints)
    check_reduction_validity(timepoints, t_reduction, 'timepoints')

    array_parameters = (min_intensities, max_intensities)
    for array_parameter in array_parameters:
        check_array_size(array_parameter, allowed=[0, 1, len(channels)], nullable=False)
    min_intensities, max_intensities = parse_intensity_bounds(in_image, channels, min_intensities, max_intensities)

    array_parameters = (gammas, filters, colormaps)
    for array_parameter in array_parameters:
        # Currently, we only allow 1 parameter to be applied to all channels
        check_array_size(array_parameter, allowed=[0, 1], nullable=False)

    # TODO: verify colormap names are valid
    # TODO: verify filter names are valid

    tile_args = {
        "in_image": in_image,
        "in_channels": channels,
        "in_z_slices": z_slices,
        "in_timepoints": timepoints,
        "tile_region": tile_region,
        "c_reduction": c_reduction,
        "z_reduction": z_reduction,
        "t_reduction": t_reduction,
        "out_width": out_width,
        "out_height": out_height,
        "out_format": out_format,
        "gammas": gammas,
        "filters": filters,
        "colormaps": colormaps,
        "min_intensities": min_intensities,
        "max_intensities": max_intensities,
        "log": log,
    }
    tile = TileResponse(**tile_args)
    fp = BytesIO(tile.get_response_buffer())
    fp.seek(0)

    headers = dict()
    add_image_size_limit_header(headers, tile_region.width, tile_region.height, out_width, out_height)
    return send_file(fp, mimetype=mimetype), headers


def show_tile_by_zoom(filepath, zoom, ti, channels=None, z_slices=None, timepoints=None,
                      c_reduction="ADD", z_reduction=None, t_reduction=None,
                      min_intensities=None, max_intensities=None, colormaps=None, filters=None,
                      gammas=None, log=None):
    return show_tile(filepath, zoom=zoom, ti=ti, channels=channels, z_slices=z_slices, timepoints=timepoints,
                     c_reduction=c_reduction, z_reduction=z_reduction, t_reduction=t_reduction,
                     min_intensities=min_intensities, max_intensities=max_intensities, colormaps=colormaps,
                     filters=filters, gammas=gammas, log=log)


def show_tile_with_body_by_zoom(filepath, zoom, ti, body):
    return show_tile_by_zoom(filepath, zoom, ti, **body)


def show_tile_by_level(filepath, level, ti, channels=None, z_slices=None, timepoints=None,
                       c_reduction="ADD", z_reduction=None, t_reduction=None,
                       min_intensities=None, max_intensities=None, colormaps=None, filters=None,
                       gammas=None, log=None):
    return show_tile(filepath, level=level, ti=ti, channels=channels, z_slices=z_slices, timepoints=timepoints,
                     c_reduction=c_reduction, z_reduction=z_reduction, t_reduction=t_reduction,
                     min_intensities=min_intensities, max_intensities=max_intensities, colormaps=colormaps,
                     filters=filters, gammas=gammas, log=log)


def show_tile_with_body_by_level(filepath, level, ti, body):
    return show_tile_by_level(filepath, level, ti, **body)


def show_tile_with_body(filepath, body):
    return show_tile(filepath, **body)


def show_tile_v1(zoomify, tileGroup, x, y, z, mimeType):
    return show_tile(filepath=zoomify, zoom=z, tx=x, ty=y)


def show_tile_v2(z, mimeType, zoomify=None, fif=None, tileGroup=None, tileIndex=None, x=None, y=None):
    if all(i is not None for i in (zoomify, tileGroup, x, y)):
        return show_tile_v1(zoomify, tileGroup, x, y, z, mimeType)
    elif all(i is not None for i in (fif, z, tileIndex)):
        return show_tile(filepath=fif, zoom=z, ti=tileIndex)
    else:
        raise BadRequestProblem(detail="Incoherent set of parameters.")
