# SilAuto API Server

This project is an api wrapper around the drafting functionality in silnlp. If you have a working silnlp installation, you can use this repo to faciliate api access to adding projects, creating align/train/translate tasks and retrieving data / downloading drafts.

## Environment Variables

| Variable                         | Description                                                        | Default         |
| ---------------------------------| ------------------------------------------------------------------ | --------------- |
| `SILNLP_DATA`                    | The folder where silnlp looks for data                             | `~/silnlp_data` |
| `MAX_CONCURRENT_FILE_PROCESSING` | Max files to process concurrently                                  | `10`            |
| `DATABASE_PATH`                  | Path to the SQLite database file (will also store WAL files)       | `./db/`        |
| `CLIENT_PATH`                    | Path to the client files                                           | `/app/client`   |

## Running the API Server

### Running Locally

To run the project locally, follow these steps:

1. **Copy the example environment file:**  
   This creates a `.env` file with default settings.  
   `cp .env.example .env`

2. **Edit the `.env` file:**  
   Update the configuration values in `.env` as needed for your local setup.

3. **Start the development server:**  
   This command runs the FastAPI app using Uvicorn with auto-reload enabled for development.  
   `uvicorn app.main:app --reload`


### Running with Docker

You can run the API server in a Docker container. This allows you to isolate dependencies and easily manage environment variables and data locations.

```bash
docker build -t silauto-api .

docker run -it --rm \
  -p 8000:8000 \
  -v /path/to/your/silnlp_data:/silnlp_data \
  -v /path/to/your/db_root:/app/db/ \
  -e SILNLP_DATA=/silnlp_data \
  -e DATABASE_PATH=/app/db/ \
  -e MAX_CONCURRENT_FILE_PROCESSING=10 \
  silauto-api
```

**Notes:**
- Adjust `/path/to/your/silnlp_data` and `/path/to/your/db_root` to your local paths.
- You can set any of the environment variables below as needed.
- You can also use a `.env` file and pass it with `--env-file .env`.
