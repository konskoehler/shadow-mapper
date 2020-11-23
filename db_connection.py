# Imports
from geoalchemy2 import Geometry
from sqlalchemy import create_engine


def write_to_sql(gdf):
    engine = create_engine('postgresql://osm_user:osm@localhost:5432/osm')

    # geodataframe['geom'] = geodataframe['geometry'].apply(lambda x: WKTElement(x.wkt, srid=<your_SRID>)

    # drop the geometry column as it is now duplicative
    # geodataframe.drop('geometry', 1, inplace=True)

    # Use 'dtype' to specify column's type
    # For the geom column, we will use GeoAlchemy's type 'Geometry'
    gdf.to_postgis('test123', engine, if_exists='append', schema='public', index=False,
               dtype=({'geometry': Geometry(geometry_type='POLYGON', srid=4326)}))

    # dtype={'geom': Geometry('POLYGON', srid=4326)}
