import pandas as pd
import pymysql

class DBConnection:
    """ Basic mySQL connection class
    """
    def __init__(self, host, user, password):
        self.host = host
        self.user = user
        self.password = password
        self.connection = pymysql.connect(host=self.host,
                                          user=self.user,
                                          password=self.password,
                                          charset='utf8mb4',
                                          cursorclass=pymysql.cursors.DictCursor)

    def query(self, sql, df=False, commit=False):
        with self.connection.cursor() as cursor:
            cursor.execute(sql)
            if commit:
                self.connection.commit()
            results = cursor.fetchall()
            if df:
                results = pd.DataFrame(results)
        return results


def time_query_stub(tmin=None,tmax=None,time_field='timestamp',first=False):
    stub = ''
    if tmin is not None or tmax is not None:
        if first is True:
            stub += ' where '
        else:
            stub += ' and '
        stub += '{}'.format(time_field)
        if tmin is None:
            stub += ' <= "{}"'.format(tmax.isoformat())
        elif tmax is None:
            stub += ' >= "{}"'.format(tmin.isoformat())
        else:
            stub += ' between "{}" and "{}"'.format(tmin.isoformat(),tmax.isoformat())
    return stub


def get_ids(db,tmin=None,tmax=None,id_field='satellite_number',time_field='timestamp',table='vault.tle',limit=None):
    query = 'select distinct {} from {}'.format(id_field,table)
    query += time_query_stub(tmin=tmin,tmax=tmax,time_field=time_field,first=True)
    if limit is not None:
        query += ' limit {}'.format(limit)
    results = db.query(query)
    results = [r[id_field] for r in results]
    return results


def build_query(ids,tmin=None,tmax=None,table='vault.tle',id_field='satellite_number',time_field='timestamp'):
    """ Build a generic `select` query letting us grab specific satellite or
        vessel IDs over a specified range of time
    """
    query = 'select * from {}'.format(table)
    cond_sep = None
    if ids is not None and len(ids) > 0:
        if cond_sep is None:
            cond_sep = "where"
        else:
            cond_sep = "and"
        query += ' {} {} in {}'.format(cond_sep,id_field,tuple(ids))
    if tmin is not None or tmax is not None:
        if cond_sep is None:
            cond_sep = "where"
        else:
            cond_sep = "and"
        query += ' {} {}'.format(cond_sep,time_field)
        if tmin is None:
            query += ' <= "{}"'.format(tmax.isoformat())
        elif tmax is None:
            query += ' >= "{}"'.format(tmin.isoformat())
        else:
            query += ' between "{}" and "{}"'.format(tmin.isoformat(),tmax.isoformat())
    return query
