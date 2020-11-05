from pims.api.exceptions import NoMatchingFormatProblem
from pims.files.file import Path


class Image(Path):
    def __init__(self, *pathsegments, factory=None):
        super().__init__(*pathsegments)

        _format = factory.match(self) if factory else None
        if _format is None:
            raise NoMatchingFormatProblem(self)
        else:
            self._format = _format

    @property
    def format(self):
        return self._format

    @property
    def width(self):
        return self._format.width

    @property
    def physical_size_x(self):
        return self._format.physical_size_x

    @property
    def height(self):
        return self._format.height

    @property
    def physical_size_y(self):
        return self._format.physical_size_y

    @property
    def depth(self):
        return self._format.depth

    @property
    def physical_size_z(self):
        return self._format.physical_size_z

    @property
    def duration(self):
        return self._format.duration

    @property
    def frame_rate(self):
        return self._format.frame_rate

    @property
    def n_channels(self):
        return self._format.n_channels

    @property
    def pixel_type(self):
        return self._format.pixel_type

    @property
    def significant_bits(self):
        return self._format.significant_bits

    @property
    def acquisition_datetime(self):
        return self._format.acquisition_datetime

    @property
    def description(self):
        return self._format.description