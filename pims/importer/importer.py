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
import logging
import shutil
from datetime import datetime

from pims.api.exceptions import FilepathNotFoundProblem, NoMatchingFormatProblem, MetadataParsingProblem, \
    BadRequestException
from pims.api.utils.models import HistogramType
from pims.files.file import Path, HISTOGRAM_STEM
from pims.files.histogram import build_histogram_file
from pims.files.image import Image
from pims.formats.utils.factories import FormatFactory, SpatialReadableFormatFactory

log = logging.getLogger("pims.app")

# TODO
PENDING_PATH = Path("/tmp/uploaded")
FILE_ROOT_PATH = Path("/data/pims")


def unique_name_generator():
    return int(datetime.now().timestamp() * 1e6)


class FileErrorProblem(BadRequestException):
    pass


class ImageParsingProblem(BadRequestException):
    pass


class FormatConversionProblem(BadRequestException):
    pass


class FileImporter:
    """
    Image importer from file. It moves a pending file to PIMS root path, tries to
    identify the file format, converts it if needed and checks its integrity.

    Attributes
    ----------
    pending_file : Path
        A file to import from PENDING_PATH directory
    pending_name : str (optional)
        A name to use for the pending file. If not provided, the current pending file name is used.
    loggers : list of ImportLogger (optional)
        A list of import loggers

    """
    def __init__(self, pending_file, pending_name=None, loggers=None):
        self.loggers = loggers if loggers is not None else []
        self.pending_file = pending_file
        self.pending_name = pending_name

        self.upload_dir = None
        self.upload_path = None
        self.original_path = None
        self.original = None
        self.spatial_path = None
        self.spatial = None
        self.histogram_path = None
        self.histogram = None

        self.processed_dir = None

    def log(self, method, *args, **kwargs):
        for logger in self.loggers:
            try:
                getattr(logger, method)(*args, **kwargs)
            except AttributeError:
                log.warning(f"No method {method} for import logger {logger}")

    def run(self, prefer_copy=False):
        """
        Import the pending file. It moves a pending file to PIMS root path, tries to
        identify the file format, converts it if needed and checks its integrity.

        Parameters
        ----------
        prefer_copy : bool
            Prefer copy the pending file instead of moving it. Useful for tests.

        Returns
        -------
        images : list of Image
            A list of images imported from the pending file.

        Raises
        ------
        FilepathNotFoundProblem
            If pending file is not found.
        """
        try:
            self.log('start_import', self.pending_file)

            # Check the file is in pending area.
            if self.pending_file.parent != PENDING_PATH or not self.pending_file.exists():
                self.log('file_not_found', self.pending_file)
                raise FilepathNotFoundProblem(self.pending_file)

            # Move the file to PIMS root path
            try:
                self.upload_dir = FILE_ROOT_PATH / Path("{}{}".format("upload", str(unique_name_generator())))
                self.upload_dir.mkdir()  # TODO: mode

                name = self.pending_name if self.pending_name else self.pending_file.name
                self.upload_path = self.upload_dir / name

                if prefer_copy:
                    shutil.copy(self.pending_file, self.upload_path)
                else:
                    shutil.move(self.pending_file, self.upload_path)
                self.log('file_moved', self.pending_file, self.upload_path)
            except (FileNotFoundError, FileExistsError, OSError) as e:
                self.log('file_not_moved', self.pending_file, exception=e)
                raise FileErrorProblem(self.pending_file)

            assert self.upload_path.has_upload_role()

            # Identify format
            self.log('start_format_detection', self.upload_path)
            format_factory = FormatFactory()
            format = format_factory.match(self.upload_path)
            if format is None:
                self.log('no_matching_format', self.upload_path)
                raise NoMatchingFormatProblem(self.upload_path)
            self.log('matching_format_found', self.upload_path, format)

            try:
                format.main_imd
            except MetadataParsingProblem as e:
                self.log('integrity_error', self.upload_path, exception=e)
                raise e

            # Create processed dir
            self.processed_dir = self.upload_dir / Path('processed')
            try:
                self.processed_dir.mkdir()  # TODO: mode
            except (FileNotFoundError, FileExistsError, OSError) as e:
                self.log('generic_file_error', self.processed_dir, exception=e)
                raise FileErrorProblem(self.processed_dir)

            # Create original role
            self.original_path = self.processed_dir / Path("{}.{}".format("original", format.get_identifier()))
            try:
                self.original_path.symlink_to(self.upload_path, target_is_directory=self.upload_path.is_dir())
            except (FileNotFoundError, FileExistsError, OSError) as e:
                self.log('generic_file_error', self.original_path, exception=e)
                raise FileErrorProblem(self.original_path)
            assert self.original_path.has_original_role()

            # Check original image integrity
            self.original = Image(self.original_path, format=format)
            errors = self.original.check_integrity(metadata=True)
            if len(errors) > 0:
                attr, e = errors[0]
                self.log('integrity_error', self.original_path, attribute=attr, exception=e)
                raise ImageParsingProblem(self.original)

            if format.is_spatial():
                self.deploy_spatial(format)
            else:
                raise NotImplementedError()

            self.deploy_histogram(self.original.get_spatial())

            # Finished
            self.log('import_success', self.upload_path, self.original)
            return [self.upload_path]
        except Exception as e:
            self.log('generic_file_error', self.upload_path, exeception=e)
            raise e

    def deploy_spatial(self, format):
        stem = 'visualisation'
        if format.need_conversion:
            try:
                ext = format.conversion_format().get_identifier()
                self.spatial_path = self.processed_dir / Path("{}.{}".format(stem, ext))
                self.log('start_conversion', self.spatial_path, self.upload_path)

                r = format.convert(self.spatial_path)
                if not r or not self.spatial_path.exists():
                    self.log('conversion_error', self.spatial_path)
                    raise FormatConversionProblem()
            except Exception as e:
                self.log('conversion_error', self.spatial_path, exception=e)
                raise FormatConversionProblem()

            spatial_format = SpatialReadableFormatFactory().match(self.spatial_path)
            if not spatial_format:
                self.log('no_matching_format', self.spatial_path)
                raise NoMatchingFormatProblem(self.spatial_path)
            self.log('matching_format_found', self.spatial_path, spatial_format)

            self.spatial = Image(self.spatial_path, format=spatial_format)
            self.log('conversion_success', self.spatial_path, self.spatial)
        else:
            # Create spatial role
            self.spatial_path = self.processed_dir / Path("{}.{}".format(stem, format.get_identifier()))
            try:
                self.spatial_path.symlink_to(self.upload_path, target_is_directory=self.upload_path.is_dir())
                self.spatial = Image(self.spatial_path, format=format)
            except (FileNotFoundError, FileExistsError) as e:
                self.log('generic_file_error', path=self.spatial_path, exception=e)
                raise FileErrorProblem(self.spatial_path)

        assert self.spatial.has_spatial_role()

        errors = self.spatial.check_integrity(metadata=True)  # TODO: check also image output
        if len(errors) > 0:
            attr, e = errors[0]
            self.log('integrity_error', self.spatial_path, attribute=attr, exception=e)
            raise ImageParsingProblem(self.spatial)

        return self.spatial

    def deploy_histogram(self, image):
        try:
            self.histogram_path = self.processed_dir / Path(HISTOGRAM_STEM)
            self.log('start_build_histogram', self.histogram_path, self.upload_path)
            self.histogram = build_histogram_file(image, self.histogram_path, HistogramType.FAST)
        except (FileNotFoundError, FileExistsError) as e:
            self.log('histogram_file_error', path=self.histogram_path, exception=e)
            raise FileErrorProblem(self.histogram_path)
