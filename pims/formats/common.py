from pims.formats.abstract import AbstractFormat


class JPEGFormat(AbstractFormat):
    def match(self):
        buf = self._imagepath.signature()
        return (len(buf) > 2 and
                buf[0] == 0xFF and
                buf[1] == 0xD8 and
                buf[2] == 0xFF)

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
    def match(self):
        buf = self._imagepath.signature()
        return (len(buf) > 3 and
                buf[0] == 0x89 and
                buf[1] == 0x50 and
                buf[2] == 0x4E and
                buf[3] == 0x47)

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
    def match(self):
        buf = self._imagepath.signature()
        return (len(buf) > 13 and
                buf[0] == 0x52 and
                buf[1] == 0x49 and
                buf[2] == 0x46 and
                buf[3] == 0x46 and
                buf[8] == 0x57 and
                buf[9] == 0x45 and
                buf[10] == 0x42 and
                buf[11] == 0x50 and
                buf[12] == 0x56 and
                buf[13] == 0x50)

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
