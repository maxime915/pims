from pims.formats.abstract import AbstractFormat


class JPEGFormat(AbstractFormat):
    @property
    def width(self):
        return 1

    @property
    def height(self):
        return 1


class PNGFormat(AbstractFormat):
    @property
    def width(self):
        return 1

    @property
    def height(self):
        return 1


class WebPFormat(AbstractFormat):
    @property
    def width(self):
        return 1

    @property
    def height(self):
        return 1
