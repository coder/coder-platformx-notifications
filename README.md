# Coder PlatformX Events Middleware

## Overview

This Flask-based middleware receives webhooks from Coder, filters relevant events, and forwards them to [PlatformX by DX](https://getdx.com/platformx) for tracking. It is designed to work well with serverless platforms such as AWS Lambda and has been tested on Google Cloud Run Functions with Buildpacks.

## Features

- Receives webhooks from Coder
- Filters tracked events based on environment configuration
- Extracts relevant user information from webhook payloads
- Forwards formatted events to PlatformX by getDX API
- Logs requests and responses for debugging

## Requirements

- Python 3.11
- See packages in [requirements.txt](./requirements.txt)

## Installation

1. Clone the repository:
   ```sh
   git clone <repo-url>
   cd <repo-directory>
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

## Supported Notification Types

This middleware supports the following [Coder notifications](https://coder.com/docs/coder/v1/latest/notifications):

- Workspace Created
- Workspace Manually Updated
- User Account Created
- User Account Suspended
- User Account Activated

## Environment Variables

Create a `.env` file in the project root and set the following variables:

```ini
LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING
GETDX_API_KEY=<your-getdx-api-key>
EVENTS_TRACKED=Workspace Created,Workspace Manually Updated,User Account Created,User Account Suspended,User Account Activated

```
