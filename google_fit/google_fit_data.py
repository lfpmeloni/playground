import os
import datetime
import pandas as pd
import matplotlib.pyplot as plt
from google.oauth2 import credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# Define the scopes for Google Fit
SCOPES = [
    'https://www.googleapis.com/auth/fitness.activity.read',
    'https://www.googleapis.com/auth/fitness.heart_rate.read'
]

def authenticate_google_fit():
    creds = None
    # Token file stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = credentials.Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    service = build('fitness', 'v1', credentials=creds)
    return service

def get_steps(service, start_time, end_time):
    data_source = 'derived:com.google.step_count.delta:com.google.android.gms:estimated_steps'
    data = service.users().dataset().aggregate(
        userId='me',
        body={
            "aggregateBy": [{"dataSourceId": data_source}],
            "bucketByTime": {"durationMillis": 86400000},  # Daily buckets
            "startTimeMillis": int(start_time.timestamp() * 1000),
            "endTimeMillis": int(end_time.timestamp() * 1000),
        }
    ).execute()
    
    steps = []
    dates = []
    for bucket in data.get('bucket', []):
        for dataset in bucket.get('dataset', []):
            for point in dataset.get('point', []):
                for value in point.get('value', []):
                    steps.append(value.get('intVal', 0))
                    start_time_millis = int(bucket['startTimeMillis'])
                    dates.append(datetime.datetime.fromtimestamp(start_time_millis / 1000, tz=datetime.timezone.utc).date())
    df_steps = pd.DataFrame({'Date': dates, 'Steps': steps})
    return df_steps

def get_heart_rate(service, start_time, end_time):
    data_source = 'derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm'
    data = service.users().dataset().aggregate(
        userId='me',
        body={
            "aggregateBy": [{"dataSourceId": data_source}],
            "bucketByTime": {"durationMillis": 86400000},  # Daily buckets
            "startTimeMillis": int(start_time.timestamp() * 1000),
            "endTimeMillis": int(end_time.timestamp() * 1000),
        }
    ).execute()
    
    heart_rates = []
    dates = []
    for bucket in data.get('bucket', []):
        hr_values = []
        for dataset in bucket.get('dataset', []):
            for point in dataset.get('point', []):
                for value in point.get('value', []):
                    hr_values.append(value.get('fpVal', 0))
        if hr_values:
            avg_hr = sum(hr_values) / len(hr_values)
            heart_rates.append(avg_hr)
            start_time_millis = int(bucket['startTimeMillis'])
            dates.append(datetime.datetime.fromtimestamp(start_time_millis / 1000, tz=datetime.timezone.utc).date())
    df_hr = pd.DataFrame({'Date': dates, 'Heart Rate': heart_rates})
    return df_hr

def get_exercises(service, start_time, end_time):
    # Ensure datetime objects are in UTC
    start_time_utc = start_time.astimezone(datetime.timezone.utc)
    end_time_utc = end_time.astimezone(datetime.timezone.utc)
    
    # Format timestamps according to RFC3339 without fractional seconds
    start_time_str = start_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    end_time_str = end_time_utc.strftime('%Y-%m-%dT%H:%M:%SZ')
    
    data = service.users().sessions().list(
        userId='me',
        startTime=start_time_str,
        endTime=end_time_str
    ).execute()
    
    exercises = []
    dates = []
    for session in data.get('session', []):
        activity = session.get('activity', 'Unknown')
        start = session.get('startTimeMillis')
        if start:
            date = datetime.datetime.fromtimestamp(int(start) / 1000, tz=datetime.timezone.utc).date()
            exercises.append(activity)
            dates.append(date)
    df_exercises = pd.DataFrame({'Date': dates, 'Exercise': exercises})
    return df_exercises

def main():
    service = authenticate_google_fit()
    
    # Define the time range (e.g., last 7 days)
    end_time = datetime.datetime.now(datetime.timezone.utc)
    start_time = end_time - datetime.timedelta(days=7)
    
    # Fetch the data
    df_steps = get_steps(service, start_time, end_time)
    df_hr = get_heart_rate(service, start_time, end_time)
    df_exercises = get_exercises(service, start_time, end_time)
    
    # Merge steps and heart rate data on Date
    df_merged = pd.merge(df_steps, df_hr, on='Date', how='outer').fillna(0)
    df_merged = df_merged.sort_values('Date')
    
    # Plot Steps and Heart Rate
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    # Plot Steps
    ax1.set_xlabel('Date')
    ax1.set_ylabel('Steps', color='tab:blue')
    ax1.bar(df_merged['Date'], df_merged['Steps'], color='tab:blue', alpha=0.6, label='Steps')
    ax1.tick_params(axis='y', labelcolor='tab:blue')
    
    # Create a second y-axis for Heart Rate
    ax2 = ax1.twinx()
    ax2.set_ylabel('Average Heart Rate (bpm)', color='tab:red')
    ax2.plot(df_merged['Date'], df_merged['Heart Rate'], color='tab:red', marker='o', label='Heart Rate')
    ax2.tick_params(axis='y', labelcolor='tab:red')
    
    # Add title and legends
    plt.title('Google Fit Data - Last 7 Days')
    fig.tight_layout()
    plt.show()
    
    # Plot Exercises
    if not df_exercises.empty:
        plt.figure(figsize=(10, 4))
        exercise_counts = df_exercises['Exercise'].value_counts()
        exercise_counts.plot(kind='bar', color='tab:green')
        plt.xlabel('Exercise Type')
        plt.ylabel('Count')
        plt.title('Exercises Logged - Last 7 Days')
        plt.tight_layout()
        plt.show()
    else:
        print("No exercises found for the selected time range.")

if __name__ == '__main__':
    main()
