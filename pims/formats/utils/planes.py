
import numpy as np


class PlanesInfo:
    def __init__(self, n_channels, depth, duration, keys=None, value_formats=None):
        self.n_channels = n_channels
        self.depth = depth
        self.duration = duration

        keys = keys if keys else []
        value_formats = value_formats if value_formats else []
        self._keys = keys
        self._data = self._init_data(keys, value_formats)

    def _init_data(self, keys, formats):
        return np.zeros(
            (self.n_channels, self.depth, self.duration),
            dtype={'names': keys, 'formats': formats}
        )

    @property
    def n_planes(self):
        return self.n_channels * self.depth * self.duration

    def set(self, c, z, t, **infos):
        plane_info = self._data[c][z][t]
        for k, v in infos.items():
            if k in self._keys:
                plane_info[k] = v

    def get(self, c, z, t, key, default=None):
        if key not in self._keys:
            return default
        return self._data[c][z][t][key]
