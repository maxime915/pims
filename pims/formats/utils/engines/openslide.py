from pims.formats.utils.engines.vips import VipsParser, VipsReader

from pyvips import Image as VIPSImage


class OpenslideVipsReader(VipsReader):
    def read_thumb(self, out_width, out_height, precomputed=False, **other):
        if precomputed:
            imd = self.format.full_imd
            if imd.associated_thumb.exists:
                return VIPSImage.openslideload(str(self.format.path), associated='thumbnail').flatten()

        return super().read_thumb(out_width, out_height, **other).flatten()

    def read_window(self, region, out_width, out_height, **other):
        if not region.is_normalized:
            raise ValueError("Region should be normalized.")

        tier = self.format.pyramid.most_appropriate_tier(out_width, out_height)
        level_page = VIPSImage.tiffload(str(self.format.path), level=tier.level)
        region = region.toint(width_scale=tier.width, height_scale=tier.height)
        return level_page.extract_area(region.left, region.top, region.width, region.height)

    def read_tile(self, tile, **other):
        tier = tile.tier
        tx, ty = tile.tx, tile.ty
        tsizex, tsizey = tier.tile_width, tier.tile_height

        level_page = VIPSImage.openslideload(str(self.format.path), level=tier.level)

        # There is no direct access to underlying tiles in vips
        # But the following computation match vips implementation so that only the tile
        # that has to be read is read.
        # https://github.com/jcupitt/tilesrv/blob/master/tilesrv.c#L461
        # TODO: is direct tile access significantly faster ?
        return level_page.extract_area(
            tx * tsizex,
            ty * tsizey,
            min(tier.width - tx * tsizex, tsizex),
            min(tier.height - ty * tsizey, tsizey)
        )

    def read_label(self, out_width, out_height, **other):
        imd = self.format.full_imd
        if imd.associated_label.exists:
            return VIPSImage.openslideload(str(self.format.path), associated='label').flatten()
        return None

    def read_macro(self, out_width, out_height, **other):
        imd = self.format.full_imd
        if imd.associated_macro.exists:
            return VIPSImage.openslideload(str(self.format.path), associated='macro').flatten()
        return None
