# Storyboard Pipeline API

FastAPI-based async storyboard generation API with Redis hot state and Supabase persistence.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Router                        │
│  POST /storyboard/code       - Code to storyboard       │
│  POST /storyboard/roadmap    - Roadmap to storyboard    │
│  GET  /storyboard/jobs/{id}  - Poll job status          │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
         ┌────────────────────────────────┐
         │   StoryboardJobManager         │
         │  (Redis + Supabase)            │
         └────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              ▼                       ▼
        ┌─────────┐            ┌──────────┐
        │  Redis  │            │ Supabase │
        │ (Hot)   │            │  (Cold)  │
        │ 1hr TTL │            │ Persist  │
        └─────────┘            └──────────┘
```

## API Endpoints

### POST /storyboard/code

Generate storyboard from code file.

**Request:**
```json
{
  "file_content": "def calculate_roi(): ...",
  "file_name": "calculator.py",
  "icp_preset": "coperniq_mep",
  "stage": "preview",
  "audience": "c_suite",
  "custom_headline": "Optional custom headline"
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "poll_url": "/storyboard/jobs/uuid"
}
```

### POST /storyboard/roadmap

Generate storyboard from roadmap screenshot.

**Request:**
```json
{
  "image_data": "base64-encoded-image",
  "icp_preset": "coperniq_mep",
  "audience": "c_suite",
  "custom_headline": "Coming Soon",
  "sanitize_ip": true
}
```

**Response (202 Accepted):**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "poll_url": "/storyboard/jobs/uuid"
}
```

### GET /storyboard/jobs/{job_id}

Poll job status and get results.

**Response (200 OK):**
```json
{
  "job_id": "uuid",
  "status": "completed",
  "result_image": "base64-encoded-png",
  "understanding": {
    "headline": "Automated ROI Calculator",
    "what_it_does": "...",
    "business_value": "...",
    "who_benefits": "...",
    "differentiator": "...",
    "pain_point_addressed": "...",
    "suggested_icon": "..."
  },
  "error_message": null,
  "execution_time_ms": 45000,
  "created_at": "2025-12-02T18:00:00Z",
  "completed_at": "2025-12-02T18:00:45Z"
}
```

**Response (200 OK - Pending):**
```json
{
  "job_id": "uuid",
  "status": "pending",
  "result_image": null,
  "understanding": null,
  "error_message": null,
  "execution_time_ms": null,
  "created_at": "2025-12-02T18:00:00Z",
  "completed_at": null
}
```

**Response (200 OK - Failed):**
```json
{
  "job_id": "uuid",
  "status": "failed",
  "result_image": null,
  "understanding": null,
  "error_message": "Gemini API timeout",
  "execution_time_ms": 90000,
  "created_at": "2025-12-02T18:00:00Z",
  "completed_at": "2025-12-02T18:01:30Z"
}
```

## Parameters

### ICP Presets
- `coperniq_mep` - MEP contractors (mechanical, electrical, plumbing)

### Stages
- `preview` - Coming soon teaser (no screenshots)
- `demo` - Video demo with screenshots
- `shipped` - Production-ready announcement

### Audiences
- `business_owner` - Small business owners ($500K-$2M revenue)
- `c_suite` - C-suite executives ($5M+ companies)
- `btl_champion` - Below-the-line champions (ops managers, project managers)

## Usage Examples

### Python (httpx)

```python
import httpx
import asyncio
import base64

async def generate_storyboard():
    async with httpx.AsyncClient() as client:
        # Start job
        response = await client.post(
            "http://localhost:8000/storyboard/code",
            json={
                "file_content": "def calculate_roi(): ...",
                "file_name": "calculator.py",
                "stage": "preview",
                "audience": "c_suite",
            },
            headers={"X-Org-ID": "my-org"},
        )
        job = response.json()
        job_id = job["job_id"]

        # Poll for completion
        while True:
            response = await client.get(f"http://localhost:8000/storyboard/jobs/{job_id}")
            result = response.json()

            if result["status"] in ["completed", "failed"]:
                break

            await asyncio.sleep(2)  # Poll every 2 seconds

        # Save result
        if result["status"] == "completed":
            png_data = base64.b64decode(result["result_image"])
            with open("storyboard.png", "wb") as f:
                f.write(png_data)
            print(f"Storyboard saved! Headline: {result['understanding']['headline']}")
        else:
            print(f"Job failed: {result['error_message']}")

asyncio.run(generate_storyboard())
```

### cURL

```bash
# Start job
JOB_ID=$(curl -X POST http://localhost:8000/storyboard/code \
  -H "Content-Type: application/json" \
  -H "X-Org-ID: my-org" \
  -d '{
    "file_content": "def calculate_roi(): pass",
    "file_name": "calculator.py",
    "stage": "preview",
    "audience": "c_suite"
  }' | jq -r '.job_id')

# Poll for completion
while true; do
  STATUS=$(curl -s http://localhost:8000/storyboard/jobs/$JOB_ID | jq -r '.status')
  echo "Status: $STATUS"

  if [[ "$STATUS" == "completed" || "$STATUS" == "failed" ]]; then
    break
  fi

  sleep 2
done

# Get result
curl -s http://localhost:8000/storyboard/jobs/$JOB_ID | jq '.result_image' -r | base64 -d > storyboard.png
echo "Storyboard saved to storyboard.png"
```

## State Management

### Redis (Hot State)
- Active jobs stored with 1-hour TTL
- Fast read/write for polling
- Automatic cleanup via TTL expiration
- Key format: `storyboard:job:{job_id}`

### Supabase (Cold Storage)
- Completed/failed jobs persisted to PostgreSQL
- Deleted from Redis after successful persistence
- Long-term storage for audit trail
- Table: `storyboard_jobs` (see `sql/002_storyboard_jobs.sql`)

### Job Lifecycle

```
1. POST /storyboard/code
   └─> Create job in Redis (status: pending)
   └─> Return 202 with job_id

2. Background task starts
   └─> Update status to processing
   └─> Run CodeToStoryboardTool
   └─> Update job with result/error
   └─> Persist to Supabase
   └─> Delete from Redis

3. Client polls GET /storyboard/jobs/{id}
   └─> Check Redis first
   └─> Fallback to Supabase if not found
   └─> Return current status
```

## Database Schema

See `sql/002_storyboard_jobs.sql` for the complete schema.

**Key columns:**
- `id` (UUID) - Job identifier
- `org_id` (TEXT) - Organization identifier
- `job_type` (TEXT) - `code_to_storyboard` or `roadmap_to_storyboard`
- `status` (TEXT) - `pending`, `processing`, `completed`, `failed`
- `input_params` (JSONB) - Request parameters
- `result_image` (TEXT) - Base64-encoded PNG
- `understanding` (JSONB) - Extracted business insights
- `error_message` (TEXT) - Error details if failed
- `execution_time_ms` (INTEGER) - Total execution time
- `created_at` (TIMESTAMPTZ) - Job creation timestamp
- `completed_at` (TIMESTAMPTZ) - Job completion timestamp

**Indexes:**
- `idx_storyboard_jobs_org_id` - Multi-tenant queries
- `idx_storyboard_jobs_status` - Status monitoring
- `idx_storyboard_jobs_created` - Recent jobs listing
- `idx_storyboard_jobs_type` - Job type analytics
- `idx_storyboard_jobs_org_status` - Composite index

## Testing

```bash
# Run all storyboard tests
python3 -m pytest tests/storyboard/ -v

# Run schema validation tests only
python3 -m pytest tests/storyboard/test_schemas.py -v

# Run with coverage
python3 -m pytest tests/storyboard/ --cov=src/storyboard --cov-report=html
```

## Environment Variables

```bash
# Required
REDIS_URL=redis://localhost:6379
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...
GOOGLE_API_KEY=...  # For Gemini

# Optional
APP_ENV=development
```

## Deployment

### Local Development

```bash
# Start Redis
docker-compose up -d redis

# Start FastAPI server
uvicorn src.api:app --reload --port 8000
```

### Production (Docker)

```bash
# Build
docker build -t conductor-ai:latest .

# Run
docker run -p 8000:8000 \
  -e REDIS_URL=redis://redis:6379 \
  -e SUPABASE_URL=https://xxx.supabase.co \
  -e SUPABASE_SERVICE_KEY=eyJ... \
  -e GOOGLE_API_KEY=... \
  conductor-ai:latest
```

## Error Handling

### 422 Validation Error
```json
{
  "detail": [
    {
      "loc": ["body", "file_content"],
      "msg": "String should have at least 1 character",
      "type": "string_too_short"
    }
  ]
}
```

### 404 Job Not Found
```json
{
  "detail": "Job 'abc-123' not found"
}
```

### Job Failed
```json
{
  "status": "failed",
  "error_message": "Gemini API timeout after 90 seconds"
}
```

## Performance

**Expected execution times:**
- Code to storyboard: 30-60 seconds
- Roadmap to storyboard: 40-70 seconds

**Bottlenecks:**
- Gemini Vision API (understanding stage): 10-20s
- Gemini Image Gen API (generation stage): 20-40s
- Network latency: 1-5s

**Optimization tips:**
- Use Redis for fast polling (< 1ms)
- Poll interval: 2-5 seconds
- Timeout: 120 seconds
- Retry failed jobs: 1 retry max

## Monitoring

### Supabase Views

```sql
-- Recent jobs
SELECT * FROM recent_storyboard_jobs LIMIT 10;

-- Job statistics
SELECT * FROM storyboard_job_stats;

-- Organization usage
SELECT * FROM storyboard_org_usage WHERE org_id = 'my-org';

-- Failed jobs (debugging)
SELECT * FROM storyboard_failures LIMIT 10;
```

### Metrics to Track
- Job success rate (completed / total)
- Average execution time
- Error rate by job type
- Peak concurrent jobs
- Redis memory usage
- Supabase storage size

## Troubleshooting

### Job stuck in "pending"
- Check background task is running
- Check Redis connection
- Check tool execution logs

### Job stuck in "processing"
- Gemini API timeout (90s default)
- Network issues
- Rate limiting

### Job failed with error
- Check error_message in response
- Check Gemini API quota
- Check input validation (file_content, image_data)

### Redis connection error
- Verify REDIS_URL is correct
- Check Redis is running: `redis-cli ping`
- Check firewall/network rules

### Supabase persistence error
- Verify SUPABASE_URL and SUPABASE_SERVICE_KEY
- Check RLS policies (service_role bypass)
- Check table exists: `SELECT * FROM storyboard_jobs LIMIT 1;`

## Contributing

When adding new features:
1. Add Pydantic schema to `src/storyboard/schemas.py`
2. Update `StoryboardJobManager` in `src/storyboard/state.py`
3. Add endpoint to `src/storyboard/router.py`
4. Write tests in `tests/storyboard/`
5. Update this README

## License

See project LICENSE file.
