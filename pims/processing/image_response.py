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
import numpy as np
from starlette.responses import Response

from pims import PIMS_SLUG_PNG
from pims.api.utils.models import Colorspace, AnnotationStyleMode, AssociatedName
from pims.processing.operations import OutputProcessor, ResizeImgOp, GammaImgOp, LogImgOp, RescaleImgOp, CastImgOp, \
    NormalizeImgOp, ColorspaceImgOp, MaskRasterOp, DrawRasterOp, TransparencyMaskImgOp, DrawOnImgOp, ColorspaceHistOp, \
    RescaleHistOp, ApplyLutImgOp


class View:
    def __init__(self, in_image, out_format, out_width, out_height, out_bitdepth=8, **kwargs):
        self.in_image = in_image

        self.out_width = out_width
        self.out_height = out_height
        self.out_format = out_format
        self.out_bitdepth = out_bitdepth
        self.out_format_params = {k.replace('out_format_', ''): v
                                  for k, v in kwargs.items() if k.startswith('out_format_')}

    @property
    def best_effort_bitdepth(self):
        if self.out_format == PIMS_SLUG_PNG:
            return min(self.out_bitdepth, 16)
        return min(self.out_bitdepth, 8)

    @property
    def max_intensity(self):
        return 2 ** self.best_effort_bitdepth - 1

    def process(self):
        pass

    def get_response_buffer(self):
        return OutputProcessor(
            self.out_format, self.best_effort_bitdepth,
            **self.out_format_params)(self.process())

    def http_response(self, mimetype, extra_headers=None):
        return Response(
            content=self.get_response_buffer(),
            headers=extra_headers,
            media_type=mimetype
        )


class MultidimView(View):
    def __init__(self, in_image, in_channels, in_z_slices, in_timepoints,
                 out_format, out_width, out_height, c_reduction, z_reduction,
                 t_reduction, **kwargs):
        super().__init__(in_image, out_format, out_width, out_height, **kwargs)
        self.in_image = in_image
        self.channels = in_channels
        self.z_slices = in_z_slices
        self.timepoints = in_timepoints

        self.c_reduction = c_reduction
        self.z_reduction = z_reduction
        self.t_reduction = t_reduction


class ProcessedView(MultidimView):
    def __init__(self, in_image, in_channels, in_z_slices, in_timepoints,
                 out_format, out_width, out_height, out_bitdepth,
                 c_reduction, z_reduction, t_reduction, gammas,
                 filters, colormaps, min_intensities, max_intensities, log,
                 colorspace=Colorspace.AUTO, **kwargs):
        super().__init__(in_image, in_channels, in_z_slices, in_timepoints,
                         out_format, out_width, out_height,
                         c_reduction, z_reduction, t_reduction,
                         out_bitdepth=out_bitdepth, **kwargs)

        self.gammas = gammas
        self.filters = filters
        self.colormaps = colormaps
        self.min_intensities = min_intensities
        self.max_intensities = max_intensities
        self.log = log
        self.colorspace = colorspace

    @property
    def gamma_processing(self):
        return any(gamma != 1.0 for gamma in self.gammas)

    @property
    def log_processing(self):
        return self.log

    @property
    def intensity_processing(self):
        return any(self.min_intensities) or \
               any(i != self.max_intensity for i in self.max_intensities)

    @property
    def filter_processing(self):
        return bool(len(self.filters))

    @property
    def filter_processing_histogram(self):
        return any([f.require_histogram() for f in self.filters])

    @property
    def filter_required_colorspace(self):
        colorspaces = [f.required_colorspace() for f in self.filters]
        if Colorspace.GRAY in colorspaces:
            return Colorspace.GRAY
        if Colorspace.COLOR in colorspaces:
            return Colorspace.COLOR
        return None

    @property
    def filter_colorspace_processing(self):
        if self.filter_required_colorspace is None:
            return False
        return (self.filter_required_colorspace == Colorspace.GRAY and
                len(self.channels) > 1) or \
               (self.filter_required_colorspace == Colorspace.COLOR and
                len(self.channels) == 1)

    @property
    def filter_colorspace(self):
        if self.filter_required_colorspace is None:
            return self.colorspace
        return self.filter_required_colorspace

    @property
    def colormap_processing(self):
        return bool(len(self.colormaps))

    @property
    def colorspace_processing(self):
        if self.colorspace == Colorspace.AUTO:
            return False
        return (self.colorspace == Colorspace.GRAY and
                len(self.channels) > 1) or \
               (self.colorspace == Colorspace.COLOR and
                len(self.channels) == 1)

    @property
    def new_colorspace(self):
        if self.colorspace == Colorspace.AUTO:
            return Colorspace.GRAY if len(self.channels) == 1 else Colorspace.COLOR
        return self.colorspace

    @property
    def float_processing(self):
        return self.intensity_processing or self.gamma_processing \
               or self.log_processing or self.colormap_processing \
               or self.filter_processing

    def math_lut(self):
        def dtype(bitdepth):
            if bitdepth > 16:
                return np.uint32
            elif bitdepth > 8:
                return np.uint16
            else:
                return np.uint8

        n_channels = len(self.channels)
        lut = np.zeros((self.in_image.max_value + 1, n_channels))
        if self.intensity_processing:
            for c in range(n_channels):
                mini = self.min_intensities[c]
                maxi = self.max_intensities[c]
                diff = maxi - mini
                lut[maxi:, c] = 1
                lut[mini:maxi, c] = np.linspace(0, 1, num=diff)
        else:
            lut = np.linspace(
                (0,) * n_channels, (1,) * n_channels,
                num=self.in_image.max_value + 1
            )

        if self.gamma_processing:
            lut = np.power(lut, self.gammas)

        if self.log_processing:
            lut = np.log1p(lut) * 1. / np.log1p(1)

        lut *= self.max_intensity
        return lut.astype(dtype(self.best_effort_bitdepth))

    def raw_view(self):
        pass

    def process(self):
        img = self.raw_view()
        img = ResizeImgOp(self.out_width, self.out_height)(img)

        if self.float_processing:
            img = ApplyLutImgOp(self.math_lut())(img)

        if self.filter_processing:
            filter_params = dict()
            if self.filter_processing_histogram:
                filter_params['histogram'] = self.process_histogram().squeeze()

            if self.filter_colorspace_processing:
                img = ColorspaceImgOp(self.filter_colorspace)(img)

            for filter_op in self.filters:
                img = filter_op(**filter_params)(img)

        if self.colorspace_processing:
            img = ColorspaceImgOp(self.new_colorspace)(img)
        return img

    def process_histogram(self):
        hist = self.in_image.histogram.channel_histogram(np.s_[:])
        if len(hist.shape) == 1:
            hist = hist.reshape((1, -1))

        # TODO: filters are computed on best_effort bitdepth while it should do on image bitdepth
        hist = RescaleHistOp(self.best_effort_bitdepth)(hist)

        if self.filter_colorspace_processing:
            hist = ColorspaceHistOp(self.filter_colorspace)(hist)
        return hist


class ThumbnailResponse(ProcessedView):
    def __init__(self, in_image, in_channels, in_z_slices, in_timepoints, out_format, out_width, out_height,
                 c_reduction, z_reduction, t_reduction, gammas, filters, colormaps, min_intensities,
                 max_intensities, log, use_precomputed, **kwargs):
        super().__init__(in_image, in_channels, in_z_slices, in_timepoints, out_format, out_width, out_height,
                         8, c_reduction, z_reduction, t_reduction, gammas, filters, colormaps,
                         min_intensities, max_intensities, log, **kwargs)

        self.use_precomputed = use_precomputed

    def raw_view(self):
        c, z, t = self.channels, self.z_slices[0], self.timepoints[0]  # TODO
        return self.in_image.thumbnail(self.out_width, self.out_height, c=c, z=z, t=t,
                                       precomputed=self.use_precomputed)


class ResizedResponse(ProcessedView):
    def __init__(self, in_image, in_channels, in_z_slices, in_timepoints, out_format, out_width, out_height,
                 c_reduction, z_reduction, t_reduction, gammas, filters, colormaps, min_intensities,
                 max_intensities, log, out_bitdepth, colorspace, **kwargs):
        super().__init__(in_image, in_channels, in_z_slices, in_timepoints, out_format, out_width, out_height,
                         out_bitdepth, c_reduction, z_reduction, t_reduction, gammas, filters, colormaps,
                         min_intensities, max_intensities, log, colorspace=colorspace, **kwargs)

    def raw_view(self):
        c, z, t = self.channels, self.z_slices[0], self.timepoints[0]  # TODO
        return self.in_image.thumbnail(self.out_width, self.out_height, c=c, z=z, t=t, precomputed=False)


class WindowResponse(ProcessedView):
    def __init__(self, in_image, in_channels, in_z_slices, in_timepoints, region, out_format, out_width, out_height,
                 c_reduction, z_reduction, t_reduction, gammas, filters, colormaps, min_intensities,
                 max_intensities, log, out_bitdepth, colorspace, annotations=None,
                 affine_matrix=None, annot_params=None, **kwargs):
        super().__init__(in_image, in_channels, in_z_slices, in_timepoints, out_format, out_width, out_height,
                         out_bitdepth, c_reduction, z_reduction, t_reduction, gammas, filters, colormaps,
                         min_intensities, max_intensities, log, colorspace=colorspace, **kwargs)

        self.region = region

        annot_params = annot_params if annot_params else dict()
        self.annotation_mode = annot_params.get('mode')
        self.annotations = annotations
        self.affine_matrix = affine_matrix
        self.background_transparency = annot_params.get('background_transparency')
        self.point_style = annot_params.get('point_cross')

    @property
    def colormap_processing(self):
        if self.colorspace == Colorspace.AUTO and self.annotation_mode == AnnotationStyleMode.DRAWING \
                and len(self.channels) == 1 and not self.annotations.is_stroke_grayscale:
            return True
        return super(WindowResponse, self).colormap_processing

    @property
    def new_colorspace(self):
        if self.colorspace == Colorspace.AUTO and self.annotation_mode == AnnotationStyleMode.DRAWING \
                and len(self.channels) == 1 and not self.annotations.is_stroke_grayscale:
            return Colorspace.COLOR
        return super(WindowResponse, self).new_colorspace

    def process(self):
        img = super(WindowResponse, self).process()

        if self.annotations and self.affine_matrix is not None:
            if self.annotation_mode == AnnotationStyleMode.CROP:
                mask = MaskRasterOp(self.affine_matrix, self.out_width, self.out_height)(self.annotations)
                img = TransparencyMaskImgOp(self.background_transparency, mask, self.out_bitdepth)(img)
            elif self.annotation_mode == AnnotationStyleMode.DRAWING:
                draw = DrawRasterOp(self.affine_matrix, self.out_width,
                                    self.out_height, self.point_style)(self.annotations)
                draw_background = DrawRasterOp.background_color(self.annotations)
                if self.colorspace_processing:
                    draw = ColorspaceImgOp(self.new_colorspace)(draw)
                img = DrawOnImgOp(draw, self.out_bitdepth, draw_background)(img)

        return img

    def raw_view(self):
        c, z, t = self.channels, self.z_slices[0], self.timepoints[0]  # TODO
        return self.in_image.window(self.region, self.out_width, self.out_height, c=c, z=z, t=t)


class TileResponse(ProcessedView):
    def __init__(self, in_image, in_channels, in_z_slices, in_timepoints, tile_region, out_format, out_width,
                 out_height, c_reduction, z_reduction, t_reduction, gammas, filters, colormaps, min_intensities,
                 max_intensities, log, **kwargs):
        super().__init__(in_image, in_channels, in_z_slices, in_timepoints, out_format, out_width, out_height,
                         8, c_reduction, z_reduction, t_reduction, gammas, filters, colormaps,
                         min_intensities, max_intensities, log, **kwargs)

        # Tile (region)
        self.tile_region = tile_region

    def raw_view(self):
        c, z, t = self.channels, self.z_slices[0], self.timepoints[0]  # TODO
        return self.in_image.tile(self.tile_region, c=c, z=z, t=t)


class AssociatedResponse(View):
    def __init__(self, in_image, associated_key, out_width, out_height, out_format, **kwargs):
        super().__init__(in_image, out_format, out_width, out_height, **kwargs)
        self.associated_key = associated_key

    def raw_view(self):
        if self.associated_key == AssociatedName.macro:
            associated = self.in_image.macro(self.out_width, self.out_height)
        elif self.associated_key == AssociatedName.label:
            associated = self.in_image.label(self.out_width, self.out_height)
        else:
            associated = self.in_image.thumbnail(self.out_width, self.out_height, precomputed=True)

        return associated

    def process(self):
        img = self.raw_view()
        img = ResizeImgOp(self.out_width, self.out_height)(img)
        return img


class MaskResponse(View):
    def __init__(self, in_image, annotations, affine_matrix, out_width, out_height, out_bitdepth, out_format, **kwargs):
        super().__init__(in_image, out_format, out_width, out_height, out_bitdepth, **kwargs)

        self.annotations = annotations
        self.affine_matrix = affine_matrix

    def process(self):
        return MaskRasterOp(self.affine_matrix, self.out_width, self.out_height)(self.annotations)


class DrawingResponse(MaskResponse):
    def __init__(self, in_image, annotations, affine_matrix, point_style,
                 out_width, out_height, out_bitdepth, out_format, **kwargs):
        super().__init__(in_image, annotations, affine_matrix, out_format,
                         out_width, out_height, out_bitdepth, **kwargs)

        self.point_style = point_style

    def process(self):
        return DrawRasterOp(self.affine_matrix, self.out_width,
                            self.out_height, self.point_style)(self.annotations)
