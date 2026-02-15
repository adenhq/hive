# Dropbox Tool

A toolkit for managing files and folders on Dropbox.

## Requirements

- `DROPBOX_ACCESS_TOKEN`: A Dropbox API access token.

## Available Tools

### `dropbox_list_folder`
List files and folders in a Dropbox directory.
- `path`: Folder path (empty string for root).

### `dropbox_upload_file`
Upload a file to Dropbox.
- `file_content`: Content of the file to upload (text).
- `dropbox_path`: Destination path in Dropbox (e.g., `/reports/daily.txt`).
- `mode`: Selects what to do if the file already exists (`add`, `overwrite`, `update`).
- `autorename`: If `True`, the file will be renamed if a conflict occurs.

### `dropbox_download_file`
Download a file from Dropbox.
- `dropbox_path`: Path to the file in Dropbox.

### `dropbox_create_shared_link`
Create a shared link for a file or folder.
- `path`: Path to the file or folder.

## Setup Instructions

1.  Go to the [Dropbox App Console](https://www.dropbox.com/developers/apps).
2.  Click **Create app**.
3.  Choose **Scoped access** and **Full Dropbox** (or **App folder** if you only need access to one folder).
4.  Name your app and click **Create**.
5.  Under the **Permissions** tab, enable:
    - `files.content.read`
    - `files.content.write`
    - `sharing.write`
    - `sharing.read`
6.  Go to the **Settings** tab and click **Generate** under "Generated access token".
7.  Add the token to your `.env` file as `DROPBOX_ACCESS_TOKEN`.
