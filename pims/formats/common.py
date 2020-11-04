from pims.formats.abstract import AbstractFormat


class JPEGFormat(AbstractFormat):
    @property
    def width(self):
        return 1

    @property
    def height(self):
        return 1

    @property
    def pixel_type(self):
        return "uint8"

    @property
    def significant_bits(self):
        return 8


class PNGFormat(AbstractFormat):
    @property
    def pixel_type(self):
        return "uint8"

    @property
    def significant_bits(self):
        return 8

    @property
    def width(self):
        return 1

    @property
    def height(self):
        return 1


class WebPFormat(AbstractFormat):
    @property
    def pixel_type(self):
        return "uint8"

    @property
    def significant_bits(self):
        return 8

    @property
    def width(self):
        return 1

    @property
    def height(self):
        return 1
