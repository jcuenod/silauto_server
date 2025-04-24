# SilAuto API Server

## Performance & Startup Optimization

If your application is taking a long time to start up, this is likely due to the scanning operations that populate caches on startup. Here are the main causes and solutions:

### Common Causes of Slow Startup

1. **Scripture file processing** - Uses `Vref` from `vref_utils` package to calculate statistics for each `MT/scripture` vref file
2. **Translation file scanning** - Recursively scans experiment directories with complex glob patterns
3. **Project file parsing** - Parses XML files for project metadata
4. **Large data directories** - Many files in SILNLP_DATA directories

### Quick Solutions

#### For Development (Fastest)

Create a `.env` file (copy from `.env.example`) and set:

```env
SKIP_HEAVY_OPERATIONS_ON_STARTUP=true
```

This will start the server immediately and populate caches on first request.

#### For Production (Optimized)

```env
MAX_CONCURRENT_FILE_PROCESSING=5  # Reduce based on your system
ENABLE_SCRIPTURE_CACHE=false      # If you don't need scripture stats
ENABLE_TRANSLATION_CACHE=false    # If you don't need translation data
```

### Diagnostic Tool

Run the startup diagnostic to identify bottlenecks:

```bash
python diagnose_startup.py
```

This will:

- Time each scanning operation individually
- Show which operations are slowest
- Provide specific recommendations
- Check if your data directories exist

### Performance Monitoring

Check the health endpoint for cache status:

```bash
curl http://localhost:8000/health
```

## Environment Variables

| Variable                           | Description                            | Default         |
| ---------------------------------- | -------------------------------------- | --------------- |
| `SILNLP_DATA`                      | The folder where silnlp looks for data | `~/silnlp_data` |
| `SKIP_HEAVY_OPERATIONS_ON_STARTUP` | Skip all scanning on startup           | `false`         |
| `MAX_CONCURRENT_FILE_PROCESSING`   | Max files to process concurrently      | `10`            |
| `ENABLE_SCRIPTURE_CACHE`           | Enable scripture file scanning         | `true`          |
| `ENABLE_TRANSLATION_CACHE`         | Enable translation file scanning       | `true`          |
| `ENABLE_PROJECT_CACHE`             | Enable project scanning                | `true`          |

## Running the Server

```bash
# With optimizations for fast startup
SKIP_HEAVY_OPERATIONS_ON_STARTUP=true uvicorn app.main:app --reload

# Or configure via .env file
cp .env.example .env
# Edit .env with your preferences
uvicorn app.main:app --reload
```
