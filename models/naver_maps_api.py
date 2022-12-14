# %%
# %pip install python-dotenv==0.21.0
# %pip install pandas==1.4.4
# %pip install requests==2.28.1

# %%
## For setting for each computer
import subprocess
import sys
import os
from os.path import join, dirname

def install(package):
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

try:
  from dotenv import load_dotenv
except ImportError:
  install('python-dotenv')
  from dotenv import load_dotenv

dotenv_path = join(dirname(__file__), '../.env')
load_dotenv(dotenv_path) ## to seperate private contents to .env file

# %%

NAVER_MAPS_API_KEY_ID = os.environ.get('NAVER_MAPS_API_KEY_ID')
NAVER_MAPS_API_KEY = os.environ.get('NAVER_MAPS_API_KEY')

# %%
### for basic python
from typing import Union, Tuple
import copy
from datetime import datetime

### for data manipulation
import pandas as pd

### for api
import requests
from IPython.display import Image, display

# %% [markdown]
# # Official API

# %%
maps_headers = {
  ################################################################
  #### NOTE: Fill the your own API KEY below. ####################
  ################################################################
  'X-NCP-APIGW-API-KEY-ID': NAVER_MAPS_API_KEY_ID,
  'X-NCP-APIGW-API-KEY': NAVER_MAPS_API_KEY
}

# %%
def getMapsHeaders(*, maps_headers=maps_headers):
  return maps_headers

# %% [markdown]
# ## Find Car Direction by Coordinates

# %%
def requestNaverMapsApi(maps_headers, maps_url_with_params):
  """
  Args:
      maps_headers ([type]): [description]
      maps_url_with_params ([type]): [description]

  Returns:
      [type]: [description]
  """
  r = requests.get(
    url=maps_url_with_params, 
    headers=maps_headers,
  )

  # print(row['params'])
  if r.status_code != 200:
    raise Exception('ERROR: ' + str(r.status_code))

  j = r.json()
  return j

def directionsCar(maps_headers, url_params, num_waypoints=5, options=['traoptimal', 'trafast', 'tracomfort']):
  if num_waypoints == 5:
    maps_url = 'https://naveropenapi.apigw.ntruss.com/map-direction/v1/driving'
  elif num_waypoints == 15:
    maps_url = 'https://naveropenapi.apigw.ntruss.com/map-direction-15/v1/driving'
  else:
    print('ERROR: num_waypoints should be 5 or 15')
    return

  maps_url_with_params = maps_url + '?' + url_params
  j = requestNaverMapsApi(maps_headers, maps_url_with_params)

  if 'currentDateTime' not in j:
    return pd.DataFrame()

  ##### Write the data into dataframe
  df = pd.DataFrame({
    'params': url_params,
    'timestamp': j['currentDateTime'] # ?????? ?????? ?????? ????????????, ISO datetime format ??????
  }, index=[0])

  for o in options:
    s = j['route'].get(o)[0]['summary']
    df[o+'Distance'] = s['distance'] # ?????? ?????? ??????(meters)
    df[o+'Duration'] = s['duration'] # ?????? ?????? ?????? ??????(milisecond(1/1000???))
    df[o+'TollFare'] = s['tollFare'] # ?????? ??????(????????????)
    df[o+'TaxiFare'] = s['taxiFare'] # ?????? ??????(????????????, ??????, ?????????, ??????, ?????? ??????)
    df[o+'FuelPrice'] = s['fuelPrice'] # ?????? ????????? ?????? ?????? ???????????? ????????? ????????? ?????????
  
  return df


def getDirectionsCar(
  dataframe:pd.DataFrame, 
  *,
  maps_headers:dict=maps_headers,
  start_latitude_column:str='startLat',
  start_longitude_column:str='startLong',
  goal_latitude_column:str='goalLat',
  goal_longitude_column:str='goalLong',
  options:list=['traoptimal', 'trafast', 'tracomfort'],
  ):

  #### ?????? ??????
  df = dataframe

  #### API ????????? ??? ????????? url_params ??????
  df['params'] = df.assign(
    p1='start=' + df[start_longitude_column].astype(str) + ',' + df[start_latitude_column].astype(str),
    p2='goal=' + df[goal_longitude_column].astype(str) + ',' + df[goal_latitude_column].astype(str),
    p3='option=' + ':'.join(options)
  ).filter(
    regex='\d$',
    axis=1,
  ).agg(
    '&'.join, 
    axis=1,
  )

  output = pd.DataFrame()
  for row in df.itertuples():
    output = pd.concat([
      output,
      directionsCar(maps_headers, row.params, options=options)
    ])
  df = pd.merge(df, output, on='params', how='left')
  df.drop(['params'], axis=1, inplace=True)
  
  return df.drop_duplicates()

# %% [markdown]
# ## Plot Marker on Map by Coordinates

# %%
def plotNaverMaps(
  dataframe:pd.DataFrame,
  *,
  maps_headers:dict=maps_headers,
  plot_width:int=500,
  plot_height:int=500,
  markers_latitude_column:str='latitude',
  markers_longitude_column:str='longitude',
  markers_label_column:Union[None, str]=None,
  ):

  maps_url = 'https://naveropenapi.apigw.ntruss.com/map-static/v2/raster'
  url_params = f'w={plot_width}&h={plot_height}'

  if markers_label_column is not None:
    url_params_markers = dataframe.assign(
      markers='markers=type:t|pos:' + dataframe[markers_longitude_column].astype(str) + ' ' + dataframe[markers_latitude_column].astype(str) + '|label:' + dataframe[markers_label_column].astype(str),
    ).filter(
      items=['markers'],
      axis=1,
    ).agg(
      '&'.join, 
      axis=0,
    ).iloc[0]
  else:
    url_params_markers = dataframe.assign(
      markers='markers=type:t|pos:' + dataframe[markers_longitude_column].astype(str) + ' ' + dataframe[markers_latitude_column].astype(str),
    ).filter(
      items=['markers'],
      axis=1,
    ).agg(
      '&'.join, 
      axis=0,
    ).iloc[0]

  NAVER_MAP_STATICMAP_URL = maps_url + '?' + url_params + '&' + url_params_markers

  request = requests.get(
    url = NAVER_MAP_STATICMAP_URL,
    headers = maps_headers,
  )

  if request.status_code == 200:
    display(Image(request.content))
  else:
    print('ERROR: ' + str(request.status_code))

# %% [markdown]
# # Unofficial API

# %% [markdown]
# ## Find Public Transportation Direction by Coordinates

# %%
def scrapNaverMaps(maps_url_with_params):
  """
  Args:
      maps_headers ([type]): [description]
      maps_url_with_params ([type]): [description]

  Returns:
      [type]: [description]
  """
  r = requests.get(
    url=maps_url_with_params, 
  )

  if r.status_code != 200:
    raise Exception('ERROR: ' + str(r.status_code))

  j = r.json()
  return j

def directionsPt(url_params):
  maps_url = 'https://map.naver.com/v5/api/transit/directions/point-to-point'
  maps_url_with_params = maps_url + '?' + url_params
  j = scrapNaverMaps(maps_url_with_params)

  if 'currentDateTime' not in j:
    return pd.DataFrame()

  ##### Write the data into dataframe
  df = pd.DataFrame()

  if j['status']=='CITY':
    
    for pt in ['paths', 'staticPaths']: # TODO: ?????? For Loop ?????? ??????
      p = j[pt]
      for idx in range(len(p)):

        dfSteps = pd.DataFrame()
        s = p[idx]['legs'][0]['steps']
        for idx2 in range(len(s)):
          dfSteps.loc[idx2, 'legIndex'] = idx2
          dfSteps.loc[idx2, 'legMode'] = s[idx2]['type']
          dfSteps.loc[idx2, 'legDepartureTime'] = s[idx2]['departureTime']
          dfSteps.loc[idx2, 'legArrivalTime'] = s[idx2]['arrivalTime']
          dfSteps.loc[idx2, 'legDistance'] = s[idx2]['distance'] # ?????? ?????? ??????(meters)
          dfSteps.loc[idx2, 'legDuration'] = s[idx2]['duration'] # ?????? ?????? ?????? ??????(minutes(1???))
          dfSteps.loc[idx2, 'legLine'] =  ';'.join({l['name'] for l in s[idx2]['routes']}) if s[idx2]['type']!='WALKING' else pd.NA # ??????????????? ??????/????????? ??????
          dfSteps.loc[idx2, 'legLineType'] =  ';'.join({l['type']['name'] for l in s[idx2]['routes']}) if s[idx2]['type']!='WALKING' else pd.NA # ??????????????? ??????/????????? ??????
          dfSteps.loc[idx2, 'legLineCount'] =  len({l['name'] for l in s[idx2]['routes']}) if s[idx2]['type']!='WALKING' else 0 # ??????????????? ??????/????????? ??????
          dfSteps.loc[idx2, 'legStationsCount'] = len(s[idx2]['stations']) # ??????/????????? ????????? ?????????/??? ???

        dfSteps = dfSteps.assign(
          lnkdIndex=idx,
          lnkdMethod=p[idx]['mode'], # TIME' ?????????, 'STATIC': ????????? ??????, None
          lnkdLabel=';'.join({l['labelText'] for l in p[idx]['pathLabels']}),
          lnkdMode=p[idx]['type'], # ?????? ?????? ?????? ??????
          lnkdDepartureTime=p[idx]['departureTime'],
          lnkdArrivalTime=p[idx]['arrivalTime'],
          lnkdDistance=p[idx]['distance'], # ?????? ?????? ??????(meters)
          lnkdDuration=p[idx]['duration'], # ?????? ?????? ?????? ??????(minutes(1???))
          lnkdDurationWait=p[idx]['waitingDuration'], # ?????? ??????(minutes(1???))
          lnkdDurationWalk=p[idx]['walkingDuration'], # ?????? ?????? ??????(minutes(1???))
          lnkdFare=p[idx]['fare'], # ?????? ?????? ?????? ??????(???)
          lnkdTransferCount=p[idx]['transferCount'], # ?????? ??????(???)
        )

        ##### Change the order of columns
        cols = dfSteps.columns.tolist()
        cols = cols[-12:] + cols[:-12]
        dfSteps = dfSteps[cols]

        df = pd.concat([df, dfSteps])
        
    df = df.assign(
      params=url_params,
      status=j['status'], # CITY | INTERCITY,
      timestamp=j['context']['currentDateTime'], # ?????? ?????? ?????? ????????????, ISO datetime format ??????
      serviceDay=j['context']['serviceDay']['name'], # ?????? / ????????? / ?????????
    )

    ##### Change the order of columns
    cols = df.columns.tolist()
    cols = cols[-4:] + cols[:-4]
    df = df[cols]

  else: #TODO: in the case of 'INTERCITY'
    print('##### INTERCITY CASE')
    return
  
  return df


# def convertDatetimeToISO # TODO: ?????? ?????? ???????????? ??????

def getDirectionsPt(
  dataframe:pd.DataFrame, 
  *,
  maps_headers:dict=maps_headers,
  start_latitude_column:str='startLat',
  start_longitude_column:str='startLong',
  goal_latitude_column:str='goalLat',
  goal_longitude_column:str='goalLong',
  departure_time_column:Union[str, None]='departureTime',
  mode:str='TIME',
  ):

  #### ?????? ??????
  df = dataframe

  #### Scraping ????????? ??? ????????? url_params ??????
  df['params'] = df.assign(
    p1='start=' + df[start_longitude_column].astype(str) + ',' + df[start_latitude_column].astype(str),
    p2='goal=' + df[goal_longitude_column].astype(str) + ',' + df[goal_latitude_column].astype(str),
    p3='departureTime=' + df[departure_time_column] if (departure_time_column is not None) and (departure_time_column in df.columns) and (~pd.isnull(df[departure_time_column])) else str(datetime.now().isoformat()),
    p4='crs=EPSG:4326',
    p5='mode=' + mode, #'TIME' ?????????, 'STATIC': ????????? ??????, None
    p6='lang=ko',
    p7='includeDetailOperation=true',
  ).filter(
    regex='\d$',
    axis=1,
  ).agg(
    '&'.join, 
    axis=1,
  )

  output = pd.DataFrame()
  for row in df.itertuples():
    output = pd.concat([
      output,
      directionsPt(row.params)
    ])
  df = pd.merge(df, output, on='params', how='left')
  df.drop(['params'], axis=1, inplace=True)
  
  return df.drop_duplicates()


