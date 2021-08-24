import logging
from enum import Enum

from cytomine.models import UploadedFile, AbstractImage, \
    AbstractSliceCollection, AbstractSlice, Property

from pims.api.utils.response import convert_quantity
from pims.config import get_settings
from pims.files.file import Path
from pims.formats.utils.metadata import parse_int
from pims.formats.utils.vips import dtype_to_bits


UploadedFile.CHECKING_INTEGRITY = 60
UploadedFile.ERROR_INTEGRITY = 61
UploadedFile.UNPACKING = 50
UploadedFile.ERROR_UNPACKING = 51
UploadedFile.UNPACKED = 106
UploadedFile.ERROR_STORAGE = UploadedFile.ERROR_DEPLOYMENT
UploadedFile.ERROR_UNEXPECTED = UploadedFile.ERROR_DEPLOYMENT
UploadedFile.IMPORTED = UploadedFile.CONVERTED

PENDING_PATH = Path(get_settings().pending_path)
FILE_ROOT_PATH = Path(get_settings().root)


class ImportEventType(str, Enum):
    START_DATA_EXTRACTION = "start_data_extraction"
    END_DATA_EXTRACTION = "end_data_extraction"
    MOVED_PENDING_FILE = "moved_pending_file"

    START_FORMAT_DETECTION = "start_format_detection"
    END_FORMAT_DETECTION = "end_format_detection"
    ERROR_NO_FORMAT = "error_no_format"

    START_INTEGRITY_CHECK = "start_integrity_check"
    END_INTEGRITY_CHECK = "end_integrity_check"
    ERROR_INTEGRITY_CHECK = "error_integrity"

    END_SUCCESSFUL_IMPORT = "end_successful_import"

    START_CONVERSION = "start_conversion"
    END_CONVERSION = "end_conversion"
    ERROR_CONVERSION = "error_conversion"

    START_UNPACKING = "start_unpacking"
    END_UNPACKING = "end_unpacking"
    ERROR_UNPACKING = "error_unpacking"
    
    START_SPATIAL_DEPLOY = "start_spatial_deploy"
    END_SPATIAL_DEPLOY = "end_spatial_deploy"
    
    START_HISTOGRAM_DEPLOY = "start_histogram_deploy"
    END_HISTOGRAM_DEPLOY = "end_histogram_deploy"
    ERROR_HISTOGRAM = "error_histogram"

    FILE_NOT_MOVED = "file_not_moved"
    FILE_NOT_FOUND = "file_not_found"
    FILE_ERROR = "generic_file_error"


class ImportListener:
    def __repr__(self):
        return self.__class__.__name__

    def start_data_extraction(self, path, *args, **kwargs):
        pass

    def moved_pending_file(self, old_path, new_path, *args, **kwargs):
        pass

    def end_data_extraction(self, path, *args, **kwargs):
        pass

    def start_format_detection(self, path, *args, **kwargs):
        pass

    def end_format_detection(self, path, format, *args, **kwargs):
        pass

    def error_no_format(self, path, *args, **kwargs):
        pass

    def start_unpacking(self, path, *args, **kwargs):
        pass

    def end_unpacking(self, path, unpacked_path, *args,
                      format=None, is_collection=False, **kwargs):
        pass

    def error_unpacking(self, path, *args, **kwargs):
        pass

    def start_integrity_check(self, path, *args, **kwargs):
        pass

    def end_integrity_check(self, path, *args, **kwargs):
        pass

    def error_integrity(self, path, *args, **kwargs):
        pass

    def start_conversion(self, path, parent_path, *args, **kwargs):
        pass

    def end_conversion(self, path, *args, **kwargs):
        pass

    def error_conversion(self, path, *args, **kwargs):
        pass

    def start_spatial_deploy(self, path, *args, **kwargs):
        pass

    def end_spatial_deploy(self, spatial_path, *args, **kwargs):
        pass

    def start_histogram_deploy(self, hist_path, image, *args, **kwargs):
        pass

    def end_histogram_deploy(self, hist_path, image, *args, **kwargs):
        pass

    def error_histogram(self, hist_path, image, *args, **kwargs):
        pass

    def end_successful_import(self, path, image, *args, **kwargs):
        pass

    def file_not_found(self, path, *args, **kwargs):
        pass

    def file_not_moved(self, path, *args, **kwargs):
        pass

    def generic_file_error(self, path, *args, **kwargs):
        pass


class CytomineListener(ImportListener):
    def __init__(self, root_id, uploaded_file_id):
        self.path_uf_mapping = dict()

        root = UploadedFile().fetch(root_id)
        self.path_uf_mapping[root.path] = root
        self.root_path = root.path

        if uploaded_file_id != root_id:
            uf = UploadedFile().fetch(uploaded_file_id)
            self.path_uf_mapping[uf.path] = uf

        self.abstract_images = []

    def _find_uf_by_id(self, id):
        return next((uf for uf in self.path_uf_mapping.values() if uf.id == id),
                    UploadedFile().fetch(id))

    def get_uf(self, path):
        uf = self.path_uf_mapping.get(str(path))
        if not uf:
            path = path.resolve()
            uf = self.path_uf_mapping.get(str(path))
            if not uf:
                raise KeyError(f"No UploadedFile found for {path}")
            self.path_uf_mapping[str(path)] = uf
        return uf

    @staticmethod
    def _corresponding_error_status(status):
        if status < 100:
            return status + 1
        else:
            return UploadedFile.ERROR_UNEXPECTED

    def propagate_error(self, uf):
        # Shouldn't be a core responsibility ?
        if uf.parent:
            parent = self._find_uf_by_id(uf.parent)
            parent.status = uf.status
            parent.update()
            self.propagate_error(parent)

    def start_data_extraction(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        uf.status = UploadedFile.EXTRACTING_DATA
        uf.update()

    def moved_pending_file(self, old_path, new_path, *args, **kwargs):
        uf = self.get_uf(old_path)
        uf.filename = str(new_path.relative_to(FILE_ROOT_PATH))
        uf.update()
        self.path_uf_mapping[str(new_path)] = uf

    def end_data_extraction(self, path, *args, **kwargs):
        pass

    def start_format_detection(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        uf.status = UploadedFile.DETECTING_FORMAT
        uf.update()

    def end_format_detection(self, path, format, *args, **kwargs):
        uf = self.get_uf(path)
        uf.contentType = format.get_identifier()  # TODO: not the content type
        uf.update()

    def error_no_format(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        uf.status = UploadedFile.ERROR_FORMAT
        uf.update()
        self.propagate_error(uf)

    def start_unpacking(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        uf.status = UploadedFile.UNPACKING
        uf.update()

    def end_unpacking(self, path, unpacked_path, *args,
                      format=None, is_collection=False, **kwargs):
        uf = self.get_uf(path)
        if is_collection:
            uf.status = UploadedFile.UNPACKED
        else:
            uf.contentType = format.get_identifier()  # TODO
            uf.size = unpacked_path.size
            filename = str(format.main_path.name)
            uf.originalFilename = filename
        uf.update()
        self.path_uf_mapping[str(unpacked_path)] = uf

    def error_unpacking(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        uf.status = UploadedFile.ERROR_UNPACKING
        uf.update()
        self.propagate_error(uf)

    def start_integrity_check(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        uf.status = UploadedFile.CHECKING_INTEGRITY
        uf.update()

    def end_integrity_check(self, path, *args, **kwargs):
        pass

    def error_integrity(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        uf.status = UploadedFile.ERROR_INTEGRITY
        uf.update()
        self.propagate_error(uf)

    def start_conversion(self, path, parent_path, *args, **kwargs):
        uf = UploadedFile()
        uf.status = UploadedFile.CONVERTING
        uf.originalFilename = path.name
        uf.filename = str(path.relative_to(FILE_ROOT_PATH))
        uf.size = 0
        uf.ext = ""
        uf.contentType = ""

        parent = self.get_uf(parent_path)
        uf.storage = parent.storage
        uf.user = parent.user
        uf.parent = parent.id
        uf.imageServer = parent.imageServer
        uf.save()
        self.path_uf_mapping[str(path)] = uf

        parent.status = UploadedFile.CONVERTING
        parent.update()

    def end_conversion(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        uf.size = path.size
        # uf.status = UploadedFile.CONVERTED
        uf.update()

    def error_conversion(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        uf.status = UploadedFile.ERROR_CONVERSION
        uf.update()
        self.propagate_error(uf)

    def start_spatial_deploy(self, path, *args, **kwargs):
        pass

    def end_spatial_deploy(self, spatial_path, *args, **kwargs):
        if not spatial_path.is_symlink():
            # The spatial path is not a symbolic link
            # -> a conversion has been performed
            uf = self.get_uf(spatial_path)
            uf.status = UploadedFile.IMPORTED
            uf.update()

    def start_histogram_deploy(self, hist_path, image, *args, **kwargs):
        pass  # TODO ?

    def end_histogram_deploy(self, hist_path, image, *args, **kwargs):
        pass  # TODO ?

    def error_histogram(self, hist_path, image, *args, **kwargs):
        pass  # TODO ?

    def end_successful_import(self, path, image, *args, **kwargs):
        uf = self.get_uf(path)

        ai = AbstractImage()
        ai.uploadedFile = uf.id
        ai.originalFilename = uf.originalFilename
        ai.width = image.width
        ai.height = image.height
        ai.depth = image.depth
        ai.duration = image.duration
        ai.channels = image.n_intrinsic_channels
        if image.physical_size_x:
            ai.physicalSizeX = round(
                convert_quantity(image.physical_size_x, "micrometers"), 6
            )
        if image.physical_size_y:
            ai.physicalSizeY = round(
                convert_quantity(image.physical_size_y, "micrometers"), 6
            )
        if image.physical_size_z:
            ai.physicalSizeZ = round(
                convert_quantity(image.physical_size_z, "micrometers"), 6
            )
        ai.fps = image.frame_rate
        ai.magnification = parse_int(image.objective.nominal_magnification)
        ai.bitPerSample = dtype_to_bits(image.pixel_type)
        ai.samplePerPixel = image.n_channels
        ai.save()
        self.abstract_images.append(ai)

        asc = AbstractSliceCollection()
        set_channel_names = image.n_intrinsic_channels == image.n_channels
        for c in range(image.n_intrinsic_channels):
            name = None
            if set_channel_names:
                name = image.channels[c].suggested_name
            for z in range(image.depth):
                for t in range(image.duration):
                    mime = "image/pyrtiff"  # TODO: remove
                    asc.append(
                        AbstractSlice(ai.id, uf.id, mime, c, z, t,
                                      channelName=name)
                    )
        asc.save()

        # ---
        # properties = PropertyCollection(ai)
        # for k, v in image.raw_metadata.items():
        #     properties.append(Property(ai, k, str(v)))
        # properties.save()
        # TODO: fix bug for DomainCollection save()
        for metadata in image.raw_metadata.values():
            Property(ai, metadata.namespaced_key, str(metadata.value)).save()
        # ---

        uf.status = UploadedFile.DEPLOYED
        uf.update()

    def file_not_moved(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        uf.status = self._corresponding_error_status(uf.status)
        uf.update()
        self.propagate_error(uf)

    def file_not_found(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        uf.status = self._corresponding_error_status(uf.status)
        uf.update()
        self.propagate_error(uf)

    def generic_file_error(self, path, *args, **kwargs):
        uf = self.get_uf(path)
        if uf.status % 2 == 0:
            # Only update error status if the status is not yet an error
            # (probably more detailed)
            uf.status = UploadedFile.ERROR_DEPLOYMENT
            uf.update()
        self.propagate_error(uf)


class StdoutListener(ImportListener):
    def __init__(self, name):
        self.log = logging.getLogger("upload.{}".format(name))

    def start_data_extraction(self, path, *args, **kwargs):
        self.log.info(f"Start import and data extraction for {path}")

    def moved_pending_file(self, old_path, new_path, *args, **kwargs):
        self.log.info(f"Moved {old_path} to {new_path}")

    def end_data_extraction(self, path, *args, **kwargs):
        self.log.info(f"Finished to extract data for {path}")

    def start_format_detection(self, path, *args, **kwargs):
        self.log.info(f"Start format detection for {path}")

    def end_format_detection(self, path, format, *args, **kwargs):
        self.log.info(f"Identified format {format.get_name()} for {path}")

    def error_no_format(self, path, *args, **kwargs):
        self.log.warning(f"No matching format for {path}")

    def start_unpacking(self, path, *args, **kwargs):
        self.log.info(f"Start unpacking archive {path}")

    def end_unpacking(self, path, unpacked_path, *args,
                      format=None, is_collection=False, **kwargs):
        self.log.info(f"The archive {path} is unpacked in directory "
                      f"{unpacked_path}.")
        if is_collection:
            self.log.info(f"{path} is a collection.")
        else:
            self.log.info(f"Identified format {format.get_name()} "
                          f"for {unpacked_path} ")

    def error_unpacking(self, path, *args, **kwargs):
        self.log.error(f"Error while unpacking archive {path} "
                       f"({str(kwargs.get('exception', ''))})")

    def start_integrity_check(self, path, *args, **kwargs):
        self.log.info(f"Start integrity check for {path}")

    def end_integrity_check(self, path, *args, **kwargs):
        self.log.info(f"{path} passed integrity check")

    def error_integrity(self, path, *args, **kwargs):
        self.log.error(f"Integrity error for {path}.")
        for integrity_error in kwargs.get('integrity_errors', []):
            attr, e = integrity_error
            self.log.error(f"- {attr}: {e}")

    def start_conversion(self, path, parent_path, *args, **kwargs):
        self.log.info(f"Start converting {parent_path} to {path}")

    def end_conversion(self, path, *args, **kwargs):
        self.log.info(f"Finished {path} conversion !")

    def error_conversion(self, path, *args, **kwargs):
        self.log.error(f"Error while converting {path}", exc_info=True)

    def start_spatial_deploy(self, path, *args, **kwargs):
        self.log.info(f"--- SPATIAL representation deployment for {path} ---")

    def end_spatial_deploy(self, spatial_path, *args, **kwargs):
        self.log.info(f"Finished to deploy spatial representation "
                      f"at {spatial_path}")

    def start_histogram_deploy(self, hist_path, image, *args, **kwargs):
        self.log.info(f"--- HISTOGRAM representation deployment for {image} ---")

    def end_histogram_deploy(self, hist_path, image, *args, **kwargs):
        self.log.info(f"Finished to deploy histogram representation "
                      f"at {hist_path}")

    def error_histogram(self, hist_path, image, *args, **kwargs):
        self.log.error(f"Failed to build histogram at {hist_path} "
                       f"for image {image} "
                       f"({kwargs.get('exception')}", exc_info=True)

    def end_successful_import(self, path, image, *args, **kwargs):
        self.log.info(f"{path} imported !")

    def file_not_found(self, path, *args, **kwargs):
        self.log.error(f"File {path} is not found", exc_info=True)

    def file_not_moved(self, path, *args, **kwargs):
        self.log.error(f"Failed to move {path}", exc_info=True)

    def generic_file_error(self, path, *args, **kwargs):
        self.log.error(f"Generic file error for {path}", exc_info=True)
