from flask import Flask, render_template, request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
import datetime

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        origin = request.form.get('origin')
        destination = request.form.get('destination')

        event = {
            'summary': f'Travel from {origin} to {destination}',
            'start': {

                # 形式：YYYY-MM-DDTHH:MM:SS+09:00
                'dateTime': start_time + ':00' + '+09:00',
                'timeZone': 'Asia/Tokyo',
            },
            'end': {
                'dateTime': end_time + ':00' + '+09:00',
                'timeZone': 'Asia/Tokyo',
            },
        }

        service = get_calendar_service()
        test = service.events().insert(calendarId='primary', body=event).execute()

        return 'Event created!'

    return render_template('index.html')

def get_calendar_service():
    scopes = ['https://www.googleapis.com/auth/calendar']
    flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", scopes=scopes)
    credentials = flow.run_local_server(port=0)

    service = build("calendar", "v3", credentials=credentials)

    return service

if __name__ == '__main__':
    app.run(debug=True)