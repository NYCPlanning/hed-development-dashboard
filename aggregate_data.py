import pandas as pd
from sqlalchemy import create_engine

##########################
# boro level management
##########################

def load_citywide_data(db, job_type, year_flag, year_start, year_end):

    conn = create_engine(db)

    # what are the year 
    df = pd.read_sql('''
    SELECT 
        --- {year_flag} as year,
        coalesce(COUNT(*), 0) as total_num_jobs,
        SUM(classa_net :: NUMERIC) as total_classa_net,
        bct2010 :: VARCHAR
        
    FROM   export_devdb

    WHERE
        {year_flag} :: NUMERIC BETWEEN {year_start} AND {year_end} 
        AND 
        job_inactive IS NULL
        AND 
        job_type IN ({job_type})
        


    GROUP  BY
        --- {year_flag},
        --- job_type, 
        bct2010
    '''.format(year_flag=year_flag, job_type=job_type, year_start=year_start, year_end=year_end), con = conn)

    # the dataframe is either aggregated across all years for one job type or simply one year is selected
    #if year == 'All Years':

        #ftd_df = df.loc[(df.job_type == job_type)].groupby('bct2010')['total_classa_net'].agg('sum').reset_index()

    #else:

        #ftd_df = df.loc[(df.job_type == job_type) & (df.year == float(year))]
    
    return df


##########################
# boro level management
##########################

def load_community_district_data(db, boro, year_flag):

    #boro_dict = {'Manhattan': 1, "Bronx": 2, "Brooklyn": 3, "Queens": 4, "Staten Island": 5}

    # connect 
    conn = create_engine(db)
   
    agg_db = pd.read_sql('''
    SELECT 
        {yf} AS year,
        comunitydist :: VARCHAR AS cd, 
        SUM(classa_net :: NUMERIC) as num_net_units
    
    FROM   
        export_devdb

    WHERE
        {yf} :: INTEGER >= 2010
        AND 
        boro::INTEGER = {slct_boro}

    GROUP BY 
        {yf},
        comunitydist
    '''.format(yf=year_flag, slct_boro=boro), con = conn)


    agg_db.dropna(subset=['num_net_units'], inplace=True)

    agg_db.cd = agg_db.cd.astype(str)

    return agg_db

##########################
# affordable data
##########################

def load_affordable_data(db, percent_flag, status, charct_flag):

    boro_dict = {'1': 'Manhattan', '2': "Bronx", '3': "Brooklyn", '4': "Queens", '5': "Staten Island"}

    conn = create_engine(db)

    # connect to housing 
    hny_units = pd.read_sql('''
    SELECT 
        SUM(classa_hnyaff :: NUMERIC) as hny_units,
        (SUM(classa_net :: NUMERIC)  - SUM(classa_hnyaff :: NUMERIC)) as other_units,
        job_status,
        boro :: VARCHAR

    FROM   export_devdb

    WHERE
        permit_year :: INTEGER >= 2014
        AND job_inactive IS NULL

    GROUP BY 
        job_status,
        boro
    ''', con = conn)

    hny_units.boro = hny_units.boro.map(boro_dict)

    df_permit = hny_units.loc[hny_units.job_status == '3. Permitted for Construction']

    df_complete = hny_units.loc[hny_units.job_status == '5. Completed Construction']

    # charateristics of housing new york units to compile
    if charct_flag == 'Income Level':

        attr_ls = ['extremely_low_income_units',
                    'very_low_income_units',
                    'low_income_units',
                    'moderate_income_units',
                    'middle_income_units',
                    'other_income_units'
                ]

        df_charct = pd.read_sql('''

        SELECT 
            SUM({0} :: INTEGER) as {0},
            SUM({1} :: INTEGER) as {1}, 
            SUM({2} :: INTEGER) as {2},
            SUM({3} :: INTEGER) as {3},
            SUM({4} :: INTEGER) as {4},
            SUM({5} :: INTEGER) as {5},
            borough 

        FROM hpd_hny_units_by_building

        GROUP BY
            borough
        '''.format(attr_ls[0], attr_ls[1], attr_ls[2], attr_ls[3], attr_ls[4], attr_ls[5]), con= conn)

    elif charct_flag == 'Bedrooms':

        attr_ls = ['studio_units',
                    '1_br_units',
                    '2_br_units',
                    '3_br_units',
                    '4_br_units',
                    '5_br_units',
                    '6_br+_units',
                    'unknown_br_units'
                    ]

        df_charct = pd.read_sql('''

        SELECT 
            SUM({0} :: INTEGER) as {0},
            SUM("{1}" :: INTEGER) as "{1}", 
            SUM("{2}" :: INTEGER) as "{2}",
            SUM("{3}" :: INTEGER) as "{3}",
            SUM("{4}" :: INTEGER) as "{4}",
            SUM("{5}" :: INTEGER) as "{5}",
            SUM("{6}" :: INTEGER) as "{6}",
            borough 

        FROM hpd_hny_units_by_building

        GROUP BY
            borough
        '''.format(attr_ls[0], attr_ls[1], attr_ls[2], attr_ls[3], attr_ls[4], attr_ls[5], attr_ls[6]), con=conn)

    else:

        attr_ls = ['counted_rental_units', 'counted_homeownership_units']

        df_charct = pd.read_sql('''

        SELECT 
            SUM({0} :: INTEGER) as {0},
            SUM({1} :: INTEGER) as {1}, 
            borough 

        FROM hpd_hny_units_by_building

        GROUP BY
            borough
        '''.format(attr_ls[0], attr_ls[1]), con= conn)
    
    if percent_flag == 'Percentage':

        for i in range(5):

            df_charct.iloc[i, :-1] = (df_charct.iloc[i, :-1] / df_charct.iloc[i, :-1].sum()) * 100

            df_permit.iloc[i, :-2] = (df_permit.iloc[i, :-2] / df_permit.iloc[i, :-2].sum()) * 100

            df_complete.iloc[i, :-2] = (df_complete.iloc[i, :-2] / df_complete.iloc[i, :-2].sum()) * 100

    #return df_permit if status == 'Incomplete' else df_complete, df_charct
    return df_complete, df_charct

##########################
# building size data 
##########################

def load_building_size_data(db):

    conn = create_engine(db)
   
    agg_db = pd.read_sql('''
    SELECT 
        complete_year AS year,
        SUM(ABS(classa_net)) as net_residential_units,
        job_type,
        CASE WHEN ABS(classa_net) BETWEEN 1 AND 2 THEN '1 to 2 unit buildings'
        WHEN ABS(classa_net) between 3 and 5 THEN '3 to 5' 
        WHEN ABS(classa_net) between 6 and 10 THEN '6 to 10'
        WHEN ABS(classa_net) between 11 and 25 THEN '11 to 25'
        WHEN ABS(classa_net) between 26 and 100 THEN '26 to 100'
        WHEN ABS(classa_net) > 100 THEN '> 100'
        END as units_class
    
    FROM   
        export_devdb

    WHERE
        complete_year::INTEGER >= 2010
        AND
        job_type <> 'Alteration'

    GROUP BY 
        complete_year,
        job_type,
        CASE WHEN ABS(classa_net) BETWEEN 1 AND 2 THEN '1 to 2 unit buildings'
        WHEN ABS(classa_net) between 3 and 5 THEN '3 to 5' 
        WHEN ABS(classa_net) between 6 and 10 THEN '6 to 10'
        WHEN ABS(classa_net) between 11 and 25 THEN '11 to 25'
        WHEN ABS(classa_net) between 26 and 100 THEN '26 to 100'
        WHEN ABS(classa_net) > 100 THEN '> 100'
        END
    ''', con = conn)

    return agg_db

##########################
# Net Effects 
##########################

def load_net_effects_data(database, job_type, x_axis, boro=None, year_start=None, year_end=None):

    conn = create_engine(database)

    if x_axis == 'By Year':

        if job_type == 'New Building and Demolition':

            job_type_str = "'New Building', 'Demolition'"

        elif job_type == 'Alteration Only':

            job_type_str = "'Alteration'"
        
        else:

            job_type_str = "'New Building', 'Demolition', 'Alteration'"

        agg_db = pd.read_sql('''

        SELECT 
            complete_year AS year,
            SUM(classa_net) as total_classa_net,
            CASE WHEN classa_net::INTEGER < 0 THEN 'units_loss' 
            WHEN classa_net::INTEGER > 0 THEN 'units_gain' 
            END as units_flag
        
        FROM   
            export_devdb

        WHERE
            complete_year::INTEGER >= 2010
            AND
            job_type IN ({job_type})
            AND 
            classa_net::INTEGER <> 0
            AND 
            boro :: INTEGER IN ({boro})

        GROUP BY 
            complete_year,
            CASE WHEN classa_net::INTEGER < 0 THEN 'units_loss' 
            WHEN classa_net::INTEGER > 0 THEN 'units_gain' 
            END 
        
        '''.format(job_type=job_type_str, boro=boro), con = conn)

    else:

        if job_type == 'New Building and Demolition':

            job_type_str = "'New Building', 'Demolition'"

        elif job_type == 'Alteration Only':

            job_type_str = "'Alteration'"
        
        else:

            job_type_str = "'New Building', 'Demolition', 'Alteration'" 

        agg_db = pd.read_sql('''

        SELECT 
            SUM(classa_net) as total_classa_net,
            comunitydist :: varchar AS cd,
            CASE WHEN classa_net::INTEGER < 0 THEN 'units_loss' 
            WHEN classa_net::INTEGER > 0 THEN 'units_gain' 
            END as units_flag
        
        FROM   
            export_devdb

        WHERE
            complete_year::INTEGER BETWEEN {year_start} AND {year_end} 
            AND
            job_type IN ({job_type})
            AND 
            classa_net::INTEGER <> 0
            AND 
            boro :: INTEGER = {boro}
            AND 
            (LEFT(comunitydist :: varchar, 1) :: INTEGER) = {boro}
            AND 
            job_inactive IS NULL

        GROUP BY 
            comunitydist,
            CASE WHEN classa_net::INTEGER < 0 THEN 'units_loss' 
            WHEN classa_net::INTEGER > 0 THEN 'units_gain' 
            END 
        
        '''.format(year_start=year_start, year_end=year_end, boro=boro, job_type=job_type_str), con = conn)

    return agg_db