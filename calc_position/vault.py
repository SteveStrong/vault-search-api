import datetime
import json as JSON

import pandas as pd
import numpy as np
import skyfield.api as sf
from geopy.distance import geodesic

import vault_db

RADIUS_EARTH = 6366.71 # radius in km implied by definition of nm (assumes spherical earth)

def gc_distance_from(lat1, lon1, distance, course,
                     ellipsoid = 'WGS-84'):
    """ Given initial lat/lon, distance in km, and course in degrees from true
        north, return final lat/lon.
        Inputs:
            lat1 [float]: Initial latitude, in degrees
            lon1 [float]: Initial longitude, in degrees
            distance [float]: Distance to move, in km
            course [float]: True course over ground, in degrees relative to true north
            ellipsoid [str or tuple]: Ellipsoid to use. See geopy.distance.ELLIPSOIDS
        Outputs:
            lat [float]: Final latitude, in degrees
            lon [float]: Final longitude, in degrees
    """
    geo = geodesic()
    if ellipsoid != 'WGS-84':
        geo.set_ellipsoid(ellipsoid)
    dest = geo.destination((lat1,lon1),course,distance=distance)
    lat = dest.latitude
    lon = dest.longitude

    return lat, lon

def gc_distance(lat1, lon1, lat2, lon2,
                ellipsoid = 'WGS-84'):
    """ Given two points in lat/lon, calculate the distance between them in km
        using the given ellipsoid. See geopy documentation for information
        about ellipsoids; default is 'WGS-84'.
    """
    geo = geodesic()
    if ellipsoid != 'WGS-84':
        geo.set_ellipsoid(ellipsoid)
    d = geo.measure((lat1,lon1),(lat2,lon2))

    return d

def course_btw_pts(lat1, lon1, lat2, lon2):
    """ Given two points in lat/lon, calculate the course between them.
        Assumes a spherical earth.
        Formula from http://www.edwilliams.org/avform.htm
    """
    lat1, lon1, lat2, lon2 = np.array([lat1, lon1, lat2, lon2])*np.pi/180. # convert lat/lon to radians
    tan1 = np.sin(lon1-lon2)*np.cos(lat2)
    tan2 = np.cos(lat1)*np.sin(lat2)-np.sin(lat1)*np.cos(lat2)*np.cos(lon1-lon2)
    return np.arctan2(tan1, tan2) % 2*np.pi

def get_neighbors(df, t, field='base_date_time'):
    """ Given a dataframe df and a reference value t, return the rows of the
        dataframe where df[field] brackets t
        - That is, this attempts to find i and j such that
          [df.iloc[i][field],df.iloc[j][field]) is the smallest interval that
          contains t.
        - Example: if t is 5 and df[field] = [2,4,6,8,10], this would return the
          rows of df where field = 4 and field = 6.
        - Returns None for the prev/next row if there is no prev/next row (thus
          returns None,None if no elements of df[field] are <= or > t, which
          normally would only happen if df has zero rows).
        - If df has some row where df[field] == t, get_neighbors() will return
          that row as prev_df and will return the next as next_df.

        Inputs:
            df [pandas.DataFrame]: Input dataframe
            t [scalar]: Ideally something where "greater than" and "less than" return a single Boolean value
            field [string]: Name of field to compare
        Outputs:
            prev_df [pandas.Series]: Row of df where df[field] immediately precedes t (or None if no row has field <= t)
            next_df [pandas.Series]: Row of df where df[field] immediately follows t (or None if no row has field > t)
    """
    df_sorted = df.sort_values(field)
    if t.tzinfo is None:
        t.replace(tzinfo=datetime.timezone.utc)
    prev_df = df_sorted[df_sorted[field] <= t]
    next_df = df_sorted[df_sorted[field] > t]
    if len(prev_df) > 0:
        prev_df = prev_df.iloc[-1]
    else:
        prev_df = None
    if len(next_df) > 0:
        next_df = next_df.iloc[0]
    else:
        next_df = None
    return prev_df, next_df


def extrapolate_ais(mmsis, t, df):
    """ Given ship ID, desired time in terrestrial time (Julian days), and a dataframe of AIS entries,
        return an approximate ship position at desired time.

        Output is a dict indexed by MMSI with the keys:
        'lat': Estimated latitude in degrees
        'lon': Estimated longitude in degrees
        'delta_t': Time differencebetween target time and nearest AIS entry
        'cog': Course over ground in degrees from true north
        'sog': Speed over ground in km/hr
        'method': Method used ("interp" = interpolation between two adjacent AIS entries, "extrap" = extrapolation from nearest AIS entry)
        'nearest_records': Two-element list of string timestamps of nearest AIS entries (element will be None if no AIS before/after target time)
        'topo': skyfield.Topos() object with latitude and longitude (used in find_hits)

        Inputs:
            mmsis [list]: List of MMSIs (ship IDs) to work on
            t [pandas.Timestamp]: Target time
            df [pandas.Dataframe]: Pandas dataframe of AIS data
        Output:
            ais [dict]: Dictionary of ship locations, courses, speeds, and interpolation method, indexed by MMSI
    """
    if t.tzinfo is None:
        t.replace(tzinfo=datetime.timezone.utc)
    ais = dict()

    for mmsi in mmsis:
        mask = df['mmsi'] == mmsi
        ship_df = df.loc[mask].copy()
        prev_df, next_df = get_neighbors(ship_df, t, field='base_date_time')
        if prev_df is None and next_df is None:
            print("No ships found with MMSI {}".format(mmsi))
        elif prev_df is None or next_df is None:
            # Ship only has AIS entrie(s) before t or after t, not bracketing
            # Assume traveling at SOG on course COG of nearest AIS entry and extrapolate forward/backward in time.
            method = 'extrap'
            if prev_df is None:
                ship_df = next_df
                nearest_records = [None,next_df['base_date_time'].isoformat()]
            else:
                ship_df = prev_df
                nearest_records = [prev_df['base_date_time'].isoformat(),None]
            speed = ship_df['sog']*1.852  # km/hr
            course = ship_df['cog']
            delta_t = (t - ship_df['base_date_time']).total_seconds()/3600.0    # hours
            distance = delta_t*speed # distance in km - will be negative if delta_t is negative
            lat1 = ship_df['lat']
            lon1 = ship_df['lon']
            # Goto return block now that we have lat1, lon1, distance, and course
        else:
            # AIS entries exist on either side of target time. Interpolate between them.
            # TODO: Could be fancier - weighted average between SOG for prev/next entries?
            #       Check if one entry is very close in time to this one and just use that one?
            method = 'interp'
            nearest_records = [prev_df['base_date_time'].isoformat(),next_df['base_date_time'].isoformat()]
            dt = (next_df['base_date_time'] - prev_df['base_date_time']).total_seconds()
            lat1 = prev_df['lat']
            lon1 = prev_df['lon']
            lat2 = next_df['lat']
            lon2 = next_df['lon']
            # Implied course between ponts, converted to degrees
            course = course_btw_pts(lat1, lon1, lat2, lon2)*180./np.pi
            # Calculate distance between points
            distance_btw = gc_distance(lat1, lon1, lat2, lon2) # returns distance in km
            # Implied average speed betweeen points
            speed = distance_btw / dt * 3600.0 # km/hr
            # Distance traveled at desired time
            delta_t = (t - prev_df['base_date_time']).total_seconds()/3600.0 # hours
            distance = speed * delta_t
            # Goto return block now that we have lat1, lon1, distance, and course

        # Calculate new location based on initial location, distance, and course
        lat, lon = gc_distance_from(lat1, lon1, distance, course)
        ais[mmsi] = {'lat':  lat, 'lon': lon, 'delta_t':delta_t,
                        'cog': course, 'sog': speed,
                        'method': method, 'nearest_records': nearest_records,
                        'topo': sf.Topos(latitude_degrees=lat, longitude_degrees=lon)}
    return ais


def find_closest_tle(t, sat_df, field='timestamp'):
    """ Given a reference time and dataframe of TLEs, finds the nearest TLE
        Inputs:
            t [pd.Timestamp]: Reference time
            sat_df [pandas.DataFrame]: DataFrame of TLEs
            field [str]: Field to compare with reference time
        Output:
            closest [pandas.Series]: Row from sat_df where sat_df[field] is closest to t
    """
    closest = sat_df.iloc[np.argmin(abs(sat_df[field] - t))]
    return closest


def horizon_angle(alt, radius_earth=RADIUS_EARTH, radians=False):
    """ Calculate angle along (spherical) Earth surface to the horizon, given altitude
        Inputs:
            alt [float]: Altitude in kilometers
            radius_earth [float]: Radius of spherical Earth (default RADIUS_EARTH = 6366.71 km)
            radians [bool]: If true, return radians. If False, convert to degrees.
        Output:
            angle [float]: Angle along surface to horizon
    """
    angle = np.arccos(alt / (alt + radius_earth))
    if radians is False:
        angle *= 180./np.pi
    return angle


def fov_earth_angle_subtended(fov,alt,radius_earth=RADIUS_EARTH,radians=False):
    """ Get angle along (spherical) Earth subtended by field of view half-angle `fov`, assuming a circular field of view.
        Inputs:
            fov [float]: Half-angle subtended by field of view in degrees
            alt [float]: Altitude above surface in kilometers
            radius_earth [float]: Radius of spherical Earth in kilometers
            radians [bool]: If False, return degrees, if True, return radians
        Output:
            angle [float]: Angle along surface subtended by FOV
    """
    # Convert FOV to radians
    fov *= np.pi/180.0
    horiz_fov = np.arcsin(radius_earth / (alt+radius_earth))

    if fov >= horiz_fov:
        angle = horizon_angle(alt,radius_earth=radius_earth,radians=True)
    else:
        angle = np.arcsin((radius_earth+alt)/radius_earth * np.sin(fov)) - fov
    if radians is False:
        angle *= 180./np.pi
    return angle


def find_hits(t, sat_df, ship_df, min_degrees=0, sids=None, vids=None, ts=None,
              satellite_id_field='satellite_number', vessel_id_field='mmsi',
              json = True):
    """ Given dataframes of TLE and AIS data and, optionally, lists of
        satellite and vessel IDs, return a dictionary containing satellite and
        vessel locations and the azimuth, elevation, and range (AER) between
        each satellite-vessel pair. Vessel positions are extrapolated based on
        surrounding AIS entries (see extrapolate_ais()).

        If `sids` or `vids` are None, will compute for every unique satellite
        or ship, respectively. The field used for satellite and vessel ID can
        be changed by setting the `satellite_id_field` or `vessel_id_field` field.

        Times are converted using Skyfield's Timescale object; this can be
        provided to avoid re-defining the Timescale object (useful if one is,
        say, calling find_hits many times).

        Output is converted to JSON if `json` is True.

        Format of output is a dict with four top-level keys:
        'utc': Timestamp of requested time
        'satellites': List of satellites - each element is a dict with satellite ID, latitude and longitude, and altitude
        'vessels': List of vessels - each element is a dict with vessel ID, latitude and longitude, speed and course, and details of position-calculation method
        'pairs': Dictionary containing AER of satellite-ship pairs, indexed by '<satellite_id>-<vessel_id>'

        Inputs:
            t [pd.Timestamp]: Reference time
            sat_df [pandas.DataFrame]: DataFrame containing satellite TLEs (should contain the text of the TLEs in 'line1' and 'line2' columns)
            ship_df [pandas.DataFrame]: DataFrame containing AIS data
            min_degrees [float]: minimum number of degrees above horizon to count as a "hit" (default 0)
            sids [list]: List of satellite IDs to consider. If None, considers all satellite IDs (default None)
            vids [list]: List of vessel IDs to consider. If None, considers all vessel IDs (default None)
            ts [skyfield.timelib.Timescale]: Skyfield timescale object (for time conversions, will be generated if not provided)
            satellite_id_field [str]: Field to use for unique satellite ID (defalt 'satellite_number')
            vessel_id_field [str]: Field to use for unique ship ID (default 'mmsi')
        Output:
            aer: Dict or JSON string, described above
    """
    if len(sat_df) == 0:
        raise LookupError("No TLE data loaded!")
    if len(ship_df) == 0:
        raise LookupError("No AIS data loaded!")
    if ts is None:
        ts = sf.load.timescale()
    if sids is None:
        sids = sat_df[satellite_id_field].unique()
    else:
        sat_df = sat_df[sat_df[satellite_id_field].isin(sids)]
    if vids is None:
        vids = ship_df[vessel_id_field].unique()
    else:
        ship_df = ship_df[ship_df[vessel_id_field].isin(vids)]

    time = ts.from_datetime(t.to_pydatetime())
    aer = {
        'utc': time.utc_iso(),
        'satellites': list(),
        'vessels': list(),
        'pairs': dict()
    }

    vessel_estimates = extrapolate_ais(vids, t, ship_df)
    for vid in vids:
        vessel_estimate = vessel_estimates[vid]
        aer['vessels'].append({'id': int(vid),
                                    'lat': vessel_estimate['lat'],
                                    'lon': vessel_estimate['lon'],
                                    'alt': 0,
                                    'method': vessel_estimate['method'],
                                    'nearest_ais': vessel_estimate['nearest_records'],
                                    'delta_t': vessel_estimate['delta_t'],
                                    'sog': vessel_estimate['sog'],
                                    'cog': vessel_estimate['cog']})
    sat_subpoint = dict()
    for sid in sids:
        this_sat_df = find_closest_tle(t, sat_df[sat_df[satellite_id_field] == sid])
        tle_text = this_sat_df['text'].split('\n')
        #this_sat = this_sat_df['satellite']
        this_sat = sf.EarthSatellite(tle_text[0],tle_text[1],ts=ts)
        sat_subpoint[sid] = this_sat.at(time).subpoint()
        horiz_angle = horizon_angle(sat_subpoint[sid].elevation.km)
        aer['satellites'].append({'id': int(sid),
                                        'lat': sat_subpoint[sid].latitude.degrees,
                                        'lon': sat_subpoint[sid].longitude.degrees,
                                        'alt': sat_subpoint[sid].elevation.km,
                                        'horizon': horiz_angle})
    for sid in sids:
        for vid in vids:
            vessel_topo = vessel_estimates[vid]['topo']
            alt,  az, distance = (sat_subpoint[sid] - vessel_topo).at(time).altaz()
            # We have a hit if satellite is above min_degrees for this ship at this time
            hit = True if alt.degrees > min_degrees else False
            aer['pairs']['{},{}'.format(sid,vid)] = {'sat_id': int(sid), 'ves_id': int(vid),
                                                            'azimuth': az.degrees,
                                                            'elevation': alt.degrees,
                                                            'range': distance.km,
                                                            'hit': hit}
    if json:
        aer = JSON.dumps(aer)
    return aer


def parse_params(params,defaults=None):
    """ Parse user input, apply a set of sensible defaults, and convert times
        to pd.Timestep objects
    """
    # Parse user input:
    print("Parsing input...")

    if defaults is None:
        defaults = {'altitude_min': 5.0,
                    'times': None,
                    'search_window': 1,
                    'sat_ids': None,
                    'sat_limit': 10,
                    'vessel_ids': None,
                    'vessel_limit': 10}

    for key in defaults.keys():
        if key not in params:
            params[key] = defaults[key]

    params['times'] = [pd.Timestamp(t) for t in params['times']]
    params['times'] = [t.replace(tzinfo=datetime.timezone.utc) if t.tzinfo is None else t for t in params['times']]
    params['search_window'] = pd.Timedelta(days=params['search_window'])
    # Compute start and stop times for data queries
    params['tmin'] = min(params['times']) - params['search_window']
    params['tmax'] = max(params['times']) + params['search_window']
    return params


class HitFinder():

    def __init__(self,params):
        # OPEN MYSQL DATABASE CONNECTION
        #self.open_db_connection()
        # LOAD BASELINE TIMESCALE FOR TIME CONVERSIONS
        self.ts = sf.load.timescale()
        # Parse user input:
        self.__params = parse_params(params)
        # Initialize other class members to None
        self.tle_df = None
        self.ais_df = None
        self.sat_ids = None
        self.vessel_ids = None


    def get_params(self):
        return self.__params

    def set_params(self,new_params):
        for key in new_params.keys():
            self.__params[key] = new_params[key]


    def open_db_connection(self,host,user,password):
        print("Opening DB connection...")
        self.db = vault_db.DBConnection(host=host,
                                        user=user,
                                        password=password)


    def get_sat_ids(self):
        if self.__params['sat_ids'] is not None:
            self.sat_ids = self.__params['sat_ids']
        else:
            print("Fetching satellite IDs")
            self.sat_ids = vault_db.get_ids(self.db,
                                            tmin=self.__params['tmin'],
                                            tmax=self.__params['tmax'],
                                            id_field='satellite_number',
                                            time_field='timestamp',
                                            table='vault.tle',
                                            limit=self.__params['sat_limit'])

    def load_tle_data(self,ids=None,tmin=None,tmax=None,ts=None,table='vault.tle',
                      id_field='satellite_number',time_field='timestamp'):
        print("Fetching TLE data for timeframe and satellite IDs")
        if ids is None:
            if self.sat_ids is None:
                self.get_sat_ids()
            ids = self.sat_ids
        if tmax is None:
            tmax = self.__params['tmax']
        if tmin is None:
            tmin = self.__params['tmin']
        tle_query = vault_db.build_query(ids=ids,
                                         tmin=tmin,tmax=tmax,
                                         table=table,
                                         id_field=id_field,
                                         time_field=time_field)
        self.tle_df = self.db.query(tle_query,df=True)
        if len(self.tle_df) == 0:
            raise LookupError('Error: query returned no TLE data. Query was {}'.format(tle_query))
        else:
            # Add UTC to timezones of timestamps
            self.tle_df['timestamp'] = self.tle_df['timestamp'].apply(lambda x: x.replace(tzinfo=datetime.timezone.utc))
            # Sort by time
            self.tle_df.sort_values('timestamp',inplace=True)


    def get_vessel_ids(self):
        if self.__params['vessel_ids'] is not None:
            self.vessel_ids = self.__params['vessel_ids']
        else:
            print("Fetching vessel IDs")
            self.vessel_ids = vault_db.get_ids(self.db,
                                               tmin=self.__params['tmin'],
                                               tmax=self.__params['tmax'],
                                               id_field='mmsi',
                                               time_field='base_date_time',
                                               table='vault.ais',
                                               limit=self.__params['vessel_limit'])

    def load_ais_data(self,ids=None,tmin=None,tmax=None,table='vault.ais',
                      id_field='mmsi',time_field='base_date_time'):
        print("Fetching AIS data for timeframe and vessel IDs")
        if ids is None:
            if self.vessel_ids is None:
                self.get_vessel_ids()
            ids = self.vessel_ids
        if tmax is None:
            tmax = self.__params['tmax']
        if tmin is None:
            tmin = self.__params['tmin']
        ais_query = vault_db.build_query(ids=ids,
                                tmin=tmin,tmax=tmax,
                                table=table,
                                id_field=id_field,
                                time_field=time_field)
        self.ais_df = self.db.query(ais_query,df=True)
        if len(self.ais_df) == 0:
            raise LookupError('Error: query returned no AIS data. Query was {}'.format(ais_query))
        else:
            self.ais_df['base_date_time'] = self.ais_df['base_date_time'].apply(lambda x: x.replace(tzinfo=datetime.timezone.utc))
            self.ais_df.sort_values('base_date_time',inplace=True)


    def find_hits(self,t,json=True):
        hits = find_hits(t,self.tle_df,self.ais_df,ts=self.ts,
                         min_degrees=self.__params['altitude_min'],json=json)
        return hits

    def find_all_hits(self,times=None,json=True):
        if times is None:
            times = self.__params['times']
        hits = list()
        for t in times:
            hits.append(self.find_hits(t,json=json))
        return hits


if __name__ == "__main__":
    # Fake user input
    mmsis = ['235091871',
             '247119100',
             '311072100',
             '257310000',
             '356352000',
             '368499000',
             '366270000',
             '366988820',
             '564902000',
             '577175000']
    user_input = {
        'altitude_min': 5.0, # degrees
        'times': [datetime.datetime(year=2004,month=5,day=d) for d in range(1,5)], # dates of interest
        'search_window': 7, # window in days around times to search for AIS/TLE data
        'sat_limit': 20, # first 20 sats with data in window
        'vessel_ids': mmsis, # list of specific vessel IDs
    }
    hitFinder = HitFinder(user_input)
    hitFinder.open_db_connection(host='vault-mysql2.conyv1ix7bv7.us-east-1.rds.amazonaws.com',
                                 user='admin',
                                 password='vault2021!')
    hitFinder.load_ais_data(tmax=datetime.datetime(year=2015,month=2,day=28))
    hitFinder.load_tle_data()
    hits = hitFinder.find_all_hits()
    print(hits)
