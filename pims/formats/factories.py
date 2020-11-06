from pims.formats import FORMATS


class FormatFactory:
    def __init__(self, formats=FORMATS.values()):
        self.formats = formats

    def match(self, path):
        for format in self.formats:
            if format(path).match():
                return format(path)

        return None


class SpatialReadableFormatFactory(FormatFactory):
    def __init__(self):
        formats = [f for f in FORMATS.values() if f.is_spatial() and f.is_readable()]
        super(SpatialReadableFormatFactory, self).__init__(formats)


class SpectralReadableFormatFactory(FormatFactory):
    def __init__(self):
        formats = [f for f in FORMATS.values() if f.is_spectral() and f.is_readable()]
        super(SpectralReadableFormatFactory, self).__init__(formats)
