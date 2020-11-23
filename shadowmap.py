#!/usr/bin/python
from __future__ import print_function
from __future__ import division
from past.utils import old_div
from heightmap import Map
from PIL import Image
import numpy
from math import sqrt, atan2
from sys import stdout
from shapely.geometry import Polygon
import matplotlib.pyplot as plt
from geopandas import GeoDataFrame
import geoplot
import db_connection

try:
    import c_shadowmap

    use_native = True
except ImportError:
    use_native = False


def update_progress(progress):
    progress = int(progress * 100)
    print('\r[{0:<10}] {1}%'.format('=' * (old_div(progress, 10)), progress), end=' ')
    stdout.flush()


class ShadowMap(Map):
    def __init__(self, lat, lng, resolution, size, proj, sun_x, sun_y, sun_z, heightmap, view_alt):
        Map.__init__(self, lat, lng, resolution, size, proj)
        self.sun_x = sun_x
        self.sun_y = sun_y
        self.sun_z = sun_z * self.resolution
        self.heightmap = heightmap
        self.view_alt = view_alt
        self.max_height = numpy.amax(self.heightmap.heights)
        self.min_height = numpy.amin(self.heightmap.heights)

    def render(self):
        if use_native:
            return c_shadowmap.calculate(self.heightmap.heights, self.sun_x, self.sun_y, self.sun_z, self.view_alt,
                                         self.max_height)
        else:
            shadowmap = numpy.zeros((self.size, self.size), dtype=int)
            for y in range(0, self.size):
                for x in range(0, self.size):
                    shadowmap[(y, x)] = 1 if self.is_lit(x, y) else 0

            return shadowmap

    def to_image(self):
        data = self.render()
        rescaled = (255.0 / data.max() * (data - data.min())).astype(numpy.uint8)
        return Image.fromarray(rescaled).transpose(Image.FLIP_TOP_BOTTOM)

    def to_latlng(self):
        data = self.render()

        polygons = []

        for x in range(data.shape[0]):
            for y in range(data.shape[1]):
                if data[x][y] == 1:
                    poly = numpy.empty((0, 2), float)
                    poly = numpy.vstack([poly, [x, y]])
                    poly = numpy.vstack([poly, [x - 1, y]])
                    poly = numpy.vstack([poly, [x - 1, y - 1]])
                    poly = numpy.vstack([poly, [x, y - 1]])
                    polygons.append(poly)

        for polygon in polygons:
            polygon *= self.resolution
            polygon[:][:, 0] += self.bounds[0]
            polygon[:][:, 1] += self.bounds[1]

        parsed_proj_polygons = [list(map(lambda coord: self.proj(coord[0], coord[1], inverse=True), polygon)) for polygon in polygons]

        shapely_polys = []

        for poly in parsed_proj_polygons:
            shapely_polys.append(Polygon(poly))

        gdf = GeoDataFrame(crs="EPSG:4326", geometry=shapely_polys)

        fig = plt.figure(dpi=120)
        #fig.axes.append(gdf.plot())
        fig.axes.append(geoplot.polyplot(gdf, figsize=(8, 4)))

        plt.show()


        #geoplot.polyplot(gdf, figsize=(20, 20))
        db_connection.write_to_sql(gdf)
        c = 2


    def is_lit(self, x0, y0):
        x1 = x0 + self.sun_x * self.size
        y1 = y0 + self.sun_y * self.size
        z = self.heightmap.heights[y0, x0] + self.view_alt
        zv = old_div(self.sun_z, sqrt(self.sun_x * self.sun_x + self.sun_y * self.sun_y))

        # Following is a Bresenham's algorithm line tracing.
        # This avoids performing lots of float calculations in
        # favor or integers, which is at least 10x faster.
        # Basic implementation taken from
        # http://stackoverflow.com/questions/2734714/modifying-bresenhams-line-algorithm
        steep = abs(y1 - y0) > abs(x1 - x0)
        if steep:
            x0, y0 = y0, x0
            x1, y1 = y1, x1

        if y0 < y1:
            ystep = 1
        else:
            ystep = -1

        deltax = abs(x1 - x0)
        deltay = abs(y1 - y0)
        error = old_div(-deltax, 2)
        y = y0

        xdir = 1 if x0 < x1 else -1
        x = x0
        while x > 0 and x < self.size and y > 0 and \
                y < self.size and z > self.min_height and z < self.max_height:
            if (steep and self.heightmap.heights[x, y] > z) or \
                    (not steep and self.heightmap.heights[y, x] > z):
                return False

            error = error + deltay
            if error > 0:
                y = y + ystep
                error = error - deltax

            x += xdir
            z += zv

        return True


def get_projection_north_deviation(proj, lat, lng):
    x1, y1 = proj(lng, lat - 0.2)
    x2, y2 = proj(lng, lat + 0.2)

    return atan2(x2 - x1, y2 - y1)


if __name__ == '__main__':
    from sys import argv
    from datetime import datetime
    from heightmap import HeightMap
    from suncalc import solar_position
    from math import sin, cos

    with open(argv[1], 'rb') as f:
        hm = HeightMap.load(f)

    t = datetime.strptime(argv[2], '%Y-%m-%d %H:%M')
    sunpos = solar_position(t, hm.lat, hm.lng)
    dev = get_projection_north_deviation(hm.proj, hm.lat, hm.lng)
    sun_x = -sin(sunpos['azimuth'] - dev) * cos(sunpos['altitude'])
    sun_y = -cos(sunpos['azimuth'] - dev) * cos(sunpos['altitude'])
    sun_z = sin(sunpos['altitude'])

    sm = ShadowMap(hm.lat, hm.lng, hm.resolution, hm.size, hm.proj, sun_x, sun_y, sun_z, hm, 1.5)
    sm.to_image().save(argv[3])
