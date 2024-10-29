# Google Fit Data Integration with Python

## Overview

Retrieve and visualize your Google Fit data (steps, heart rate, exercises) using Python. The script fetches data from the last seven days and displays it using matplotlib.

## Features

- **Data Retrieval**: Steps, average heart rate, and exercise sessions.
- **Visualization**: Bar charts for steps and exercises, line chart for heart rate.
- **Authentication**: OAuth2 handled automatically with token storage.

## Prerequisites

- **Python 3.6+**
- **Google Account** with Google Fit data.
- **Google Cloud Project** with Google Fit API enabled.

## Setup

### 1. Google Cloud Project

1. **Create Project**:
   - Go to [Google Cloud Console](https://console.cloud.google.com/).
   - Create a new project.

2. **Enable Google Fit API**:
   - Navigate to **APIs & Services > Library**.
   - Search for **Google Fit API** and enable it.

3. **Configure OAuth Consent**:
   - Go to **APIs & Services > OAuth consent screen**.
   - Select **External** and fill in required details.
   - Add scopes:
     - `https://www.googleapis.com/auth/fitness.activity.read`
     - `https://www.googleapis.com/auth/fitness.heart_rate.read`
   - Save and continue.

4. **Create OAuth Credentials**:
   - Navigate to **APIs & Services > Credentials**.
   - Click **Create Credentials > OAuth client ID**.
   - Choose **Desktop app** and name it.
   - Download the `credentials.json` file and place it in your project directory.

### 2. Python Environment

1. **Install Dependencies**:

    pip install --upgrade google-api-python-client google-auth-httplib2 google-auth-oauthlib matplotlib pandas

2. ** Prepare the Script:

- Ensure `credentials.json` is in the same folder as `google_fit_data.py`.

## Usage

### 1. Run the Script

Execute the Python script:
`python google_fit_data.py`

### 2. Authenticate

- A browser window will open for Google account authorization.
- After granting access, data will be fetched and plots displayed.

## API Parameters

Scopes:

- fitness.activity.read
- fitness.heart_rate.read

Data Sources:

- Steps: derived:com.google.step_count.delta:com.google.android.gms:estimated_steps
- Heart Rate: derived:com.google.heart_rate.bpm:com.google.android.gms:merge_heart_rate_bpm

Sessions Endpoint:

- sessions().list(userId='me', startTime='RFC3339', endTime='RFC3339')

## Security

Protect Credentials:

- Keep credentials.json and token.json secure.
- Add them to .gitignore to prevent exposure in version control.

## Troubleshooting

Authentication Issues:

- Delete token.json and rerun the script to re-authenticate.

Invalid Timestamps:

- Ensure timestamps are in RFC3339 format without fractional seconds.

No Data Retrieved:

- Verify Google Fit has data for the selected period.
- Check data source IDs are correct.

## License

MIT License

**Disclaimer: Use this script responsibly and comply with Google's API terms of service.**
