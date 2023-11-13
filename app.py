import os
import pickle
from re import A
from flask import Flask, render_template, request, redirect
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import datetime
from datetime import datetime
import dateutil.parser
import requests
import json
import pandas as pd



app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start = request.form.get('start_time')
        end = request.form.get('end_time')
        origin = request.form.get('origin')
        destination = request.form.get('destination')
        
        # "YYYYMMDD", "HHMM"に変換
        start_date, start_time = trans_time(start)
        end_date, end_time = trans_time(end)
        
        #データ取得
        df = pd.read_csv('spot.csv')
        df = df.sort_values(['おすすめ度(0~1or1~5)'], ascending=False)

        #駅名取得
        origin_station = SearchStationName(origin)
        destination_station = SearchStationName(destination)
        #往復経路検索
        going_route = SearchRoute(origin_station,destination_station,start_date,1,start_time)
        return_route = SearchRoute(destination_station,origin_station,end_date,2,end_time)
        
        #往復経路 list
        going_list = get_itinerary_list(going_route)
        return_list = get_itinerary_list(return_route)

        #旅程取得
        itinerary=get_itinerary(going_route,return_route,df)
        itinerary_list=get_itinerary_list(itinerary)
        schedule=going_list+itinerary_list+return_list
        #print(schedule)
        for i, cur_event in enumerate(schedule):
            if isinstance(cur_event, list):
                date=schedule[i-1]["date"]
                from_time=schedule[i-1]["toTime"]
                to_time=timer(from_time,"0100")
                from_time_iso = combine_to_iso8601(date, from_time)
                to_time_iso = combine_to_iso8601(date, to_time)
                event = {
                    'summary': f' {cur_event[0]["観光地名"]} ',
                    'description': f'{cur_event[0]["ラベル"]} ',
                    'start': {

                        # 形式：YYYY-MM-DDTHH:MM:SS+09:00
                        'dateTime': from_time_iso,
                        'timeZone': 'Asia/Tokyo',
                    },
                    'end': {
                        'dateTime': to_time_iso,
                        'timeZone': 'Asia/Tokyo',
                    },
                }

            else:
                print(cur_event)
                date=cur_event["date"]
                from_time=cur_event["fromTime"]
                to_time=cur_event["toTime"]
                from_time_iso = combine_to_iso8601(date, from_time)
                to_time_iso = combine_to_iso8601(date, to_time)
                event = {
                    'summary': f'Move from {cur_event["from"]} to {cur_event["to"]}',
                    'description': f'路線 {cur_event["rosen"]}',
                    'start': {

                        # 形式：YYYY-MM-DDTHH:MM:SS+09:00
                        'dateTime': from_time_iso,
                        'timeZone': 'Asia/Tokyo',
                    },
                    'end': {
                        'dateTime': to_time_iso,
                        'timeZone': 'Asia/Tokyo',
                    },
                }
      
            service = get_calendar_service()
            created_event = service.events().insert(calendarId='primary', body=event).execute()

        # return f'Event created! Check it at <a href="{created_event.get("htmlLink")}">here</a>'
        return redirect(created_event.get('htmlLink'))

    return render_template('index.html')


def get_calendar_service():
    scopes = ['https://www.googleapis.com/auth/calendar']
    # トークンを保存するファイルパス
    token_path = 'token.pickle'

    # 保存されたトークンが存在するかチェック
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            credentials = pickle.load(token)
    else:
        flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", scopes=scopes)
        credentials = flow.run_local_server(port=0)

        with open(token_path, 'wb') as token:
            pickle.dump(credentials, token)

    # Google Calendar APIのサービスを作成
    service = build("calendar", "v3", credentials=credentials)
    

    return service

#駅名検索
def SearchStationName(point):
    url = "https://cloud.jorudan.biz/api/gae.cgi"
    point_utf=point.encode('utf-8')
    payload = { "ak":"PFQjj7vfteTlmaTu",
                "f":"1",
                "opt1":point_utf,
                "opt4":1}
    r = requests.get(url, params=payload)
    r.json()
    return r.json()['NorikaeBizApiResult']['body']['eki'][0]['name']

#経路検索　行　発時刻　指定 1で出発時間,2で到着時間指定
def SearchRoute(point_eki,target_eki,date,mode,time):
    url = "https://cloud.jorudan.biz/api/sr.cgi"
    #point=point.encode('utf-8')
    #target=target.encode('utf-8')
    payload = {"ak":"PFQjj7vfteTlmaTu",
               "f":"1",
               "eki1":point_eki,
               "eki2":target_eki,
               "date":date,
               "time":time,
               "opt3":mode}
    gor = requests.get(url, params=payload)
    #gor.json()
    r=gor.json()['NorikaeBizApiResult']['body']['route'][0]['path']#['name']
    return r

#buffer
def timer(time1,time2):
    time1=int(time1)
    time2=int(time2)

    # 時間と分を分ける
    hours1, minutes1 = divmod(time1, 100)
    hours2, minutes2 = divmod(time2, 100)

    # 分単位で時間を計算
    total_minutes = (minutes1 + minutes2) % 60

    # 時間単位で繰り上がりを計算
    carry_hours = (hours1 + hours2 + (minutes1 + minutes2) // 60) % 24

    # 時間と分を合わせて新しい時間を作成
    result = (carry_hours * 100) + total_minutes

    # 結果を文字列としてフォーマット
    result_str = '{:04d}'.format(result)
    return result_str  # '1300' が出力されます

#a → c1..n → b SearchRoute
def get_itinerary(going_route,return_route,df):
    true_route = []
    po=going_route[-1]["to"]#現在値
    potime=going_route[-1]["toTime"]#現在時刻
    podate=going_route[-1]["toDate"]#日付け

    b=return_route[0]["from"]#帰り駅
    end_mid_time=return_route[0]["fromTime"]#タイムリミット

    dict_df = df.to_dict(orient='records')

    for i in range(len(df)):
        if po == df.iloc[i,2]:#現在値がすでに目的地　1時間遊ぶだけ　次の場所へ
            potime=timer(potime,'0100')#バッファ
            true_route.append([dict_df[i]])########
            continue     
        
        #ctoc2 route limit(c2tob)
        po_to_c=SearchRoute(po,df.iloc[i,2],podate,1,potime)
        if df.iloc[i,2]==b:
            ctob_time=timer(po_to_c[-1]["toTime"],'0100')
        else:
            c_to_b=SearchRoute(df.iloc[i, 2],b,podate,1,timer(po_to_c[-1]["toTime"],'0100'))
            ctob_time=c_to_b[-1]["toTime"]
        print("ctob {}",ctob_time)
        
        if po == b:
            if ctob_time > end_mid_time:
                print("現在値が大分で、次の場所に行くには時間がなさすぎるため終了")
                i=i+1
                continue
    #             break
            else:
                print("大分発")
                for j in po_to_c:
                    true_route.append(j)
                potime=po_to_c[-1]["toTime"]
                true_route.append([dict_df[i]])######            
                potime=timer(potime,'0100')
                po=po_to_c[-1]["to"]
                continue
        
        #ctob route time
        po_to_b=SearchRoute(po,b,podate,1,potime)   
        potob_time = po_to_b[-1]["toTime"]
        print("potob {}",potob_time)
        if end_mid_time > potob_time and ctob_time >end_mid_time:#時間切れ 
            print("time up")
            for j in po_to_b:
                true_route.append(j)
            potime=potob_time
            po=po_to_b[-1]["to"]
            break
        else:
            print("continue")
            for j in po_to_c:
                true_route.append(j)
            potime=po_to_c[-1]["toTime"]
            true_route.append([dict_df[i]])#####
            potime=timer(potime,'0100')
            po=po_to_c[-1]["to"]
            
            if i == len(df)-1 and po != b:
                print("return")
                for j in c_to_b:
                    true_route.append(j)
                potime=ctob_time
                po=c_to_b[-1]["to"]
    return true_route

##必要な要素抜き出し
def get_itinerary_list(true_route):
    itinerary=[]
    for i in true_route:
        if isinstance(i, list):
            itinerary.append(i)
        else:
            a={
                #"id":ii,

                "rosen":i["rosen"],
                "from":i["from"],
                "to":i["to"],
                "date":i["fromDate"],
                "fromTime":i["fromTime"],
                "toTime":i["toTime"]
            }

            itinerary.append(a)
    return itinerary

#iso8601 to "YYYYMMDD", "HHMM"
def trans_time(date_time):
    time_obj = datetime.strptime(date_time, "%Y-%m-%dT%H:%M")
    # "YYYYMMDD"
    date = time_obj.strftime("%Y%m%d")
    # "HHMM"
    time = time_obj.strftime("%H%M")

    return date,time

#"YYYYMMDD", "HHMM" to iso8601
def combine_to_iso8601(date_str, time_str):
    date_obj = datetime.strptime(date_str, "%Y%m%d")
    time_obj = datetime.strptime(time_str, "%H%M").time()

    # 日付と時間を結合
    combined_datetime = datetime.combine(date_obj.date(), time_obj)

    # タイムゾーン情報を直接追加
    iso8601_str = combined_datetime.strftime("%Y-%m-%dT%H:%M:%S") + "+09:00"

    return iso8601_str

if __name__ == '__main__':
    app.run(debug=True)
