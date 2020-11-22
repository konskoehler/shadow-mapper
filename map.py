from __future__ import division
from past.utils import old_div
import pickle

class Map():
    def __init__(self, lat, lng, resolution, size, proj):
        self.lat = lat
        self.lng = lng
        self.resolution = resolution
        self.size = size
        self.psize = size * resolution
        self.proj = proj
        cx, cy = proj(lng, lat)

        self.bounds = (
            cx - old_div(self.psize, 2),
            cy - old_div(self.psize, 2),
            cx + old_div(self.psize, 2),
            cy + old_div(self.psize, 2),
            )

        w, s = proj(self.bounds[0], self.bounds[1], inverse=True)
        e, n = proj(self.bounds[2], self.bounds[3], inverse=True)

        self.ll_bounds = (s, w, n, e)

    def _latLngToIndex(self, lat, lng):
        x, y = self.proj(lng, lat)
        return (
            old_div((x - self.bounds[0]), self.psize) * self.size,
            old_div((y - self.bounds[1]), self.psize) * self.size)

    def save(self, f):
        pickle.dump(self, f, pickle.HIGHEST_PROTOCOL)

    @staticmethod
    def load(f):
        return pickle.load(f)
