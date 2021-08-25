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
# import pytest
#
# from pims.processing.adapters import *
# from pims.processing.operations import RescaleImgOp, GammaImgOp, NormalizeImgOp, LogImgOp
#
# import numpy as np
#
#
# def fake_image(width, height, channels, max_value=255, dtype="float64"):
#     np_image = np.random.randint(0, max_value + 1, (height, width, channels))
#     np_image = np_image.astype(dtype)
#     vips_image = numpy_to_vips(np_image)
#     return np_image, vips_image
#
#
# def fake_normalized_image(width, height, channels):
#     np_image = np.random.rand(height, width, channels)
#     vips_image = numpy_to_vips(np_image)
#     return np_image, vips_image
#
#
# def _test_imgop(np_image, vips_image, op, expected, exact_equal=False, rtol=1e-07):
#     np_processed = op._numpy_impl(np_image)
#     vips_processed = op._vips_impl(vips_image)
#     vips_processed = vips_to_numpy(vips_processed)
#
#     if not exact_equal:
#         np.testing.assert_allclose(expected, np_processed, rtol)
#         np.testing.assert_allclose(expected, vips_processed, rtol)
#     else:
#         np.testing.assert_array_equal(expected, np_processed)
#         np.testing.assert_array_equal(expected, vips_processed)
#
#
# @pytest.mark.parametrize("bitdepth", (1, 8, 16))
# @pytest.mark.parametrize("channels", (1, 3))
# def test_rescale_img_op(bitdepth, channels):
#     np_image, vips_image = fake_normalized_image(50, 100, channels)
#     rescale = RescaleImgOp(bitdepth)
#     expected = np_image * ((2 ** bitdepth) - 1)
#
#     _test_imgop(np_image, vips_image, rescale, expected, exact_equal=True)
#
#
# @pytest.mark.parametrize("gamma", (1, 0.5, 0.25, 2, 4))
# @pytest.mark.parametrize("channels", (1, 3))
# def test_gamma_img_op(gamma, channels):
#     np_image, vips_image = fake_normalized_image(50, 100, channels)
#     gammas = [gamma] * channels
#     op = GammaImgOp(gammas)
#     expected = np_image ** gammas[0]
#
#     _test_imgop(np_image, vips_image, op, expected)
#
#
# @pytest.mark.parametrize("min_intensities", ([0, 20, 100], [0, 0, 0], [254, 100, 50]))
# @pytest.mark.parametrize("max_intensities", ([255, 200, 110], [255, 255, 255]))
# @pytest.mark.parametrize("channels", (1, 3))
# def test_normalize_img_op(min_intensities, max_intensities, channels):
#     np_image, vips_image = fake_image(50, 100, channels)
#     op = NormalizeImgOp(min_intensities[:channels], max_intensities[:channels])
#
#     expected = np.zeros_like(np_image)
#     for c in range(channels):
#         expected[:, :, c] = (np_image[:, :, c] - min_intensities[c]) / (max_intensities[c] - min_intensities[c])
#
#     _test_imgop(np_image, vips_image, op, expected)
#
#
# @pytest.mark.parametrize("channels", (1, 3))
# def test_log_img_op(channels):
#     np_image, vips_image = fake_normalized_image(50, 100, channels)
#     op = LogImgOp([1] * channels)
#
#     expected = np.log1p(np_image) * (op.max_intensities / np.log1p(op.max_intensities))
#     _test_imgop(np_image, vips_image, op, expected)
