# no-more-sql

### RAG Implementation

Use this code to run streamlit dashboard to use RAG-LLM to generate SQL queries

```
poetry run streamlit run code/main.py
```

## Server Management

The application runs as a systemd service on the server. Here's how to manage it:

### Basic Service Controls

Start the service:

```
sudo systemctl start no-more-sql
```

Stop the service:

```
sudo systemctl stop no-more-sql
```

Restart the service (after making changes):

```
sudo systemctl restart no-more-sql
```

Check service status (to see which url app is being hosted on):

```
sudo systemctl status no-more-sql
```

### Viewing Logs

View live logs (follow mode):

```
sudo journalctl -u no-more-sql -f
```

View recent logs (last 50 entries):

```
sudo journalctl -u no-more-sql -n 50
```

View logs since last server boot:

```
sudo journalctl -u no-more-sql -b
```

### Making Changes

1. All code changes in the repository directory (/home/porwals/GitHub/projects/no-more-sql) will be picked up by the service.
2. After making changes, restart the service to apply them:

```
sudo systemctl restart no-more-sql
```

### Adding New Dependencies

If you need to add new Python packages:

1. Activate the virtual environment:

```
cd /home/porwals/GitHub/projects/no-more-sql
source .venv/bin/activate
```

2. Install new package:

```
uv add new-package
```

3. Update requirements.txt:

```
pip freeze > requirements.txt
```

4. Restart the service:

```
sudo systemctl restart no-more-sql
```

### Service Configuration

The service configuration is located at /etc/systemd/system/no-more-sql.service. If you need to modify the service configuration:

1. Edit the service file:

```
sudo nano /etc/systemd/system/no-more-sql.service
```

2. Reload systemd configuration:

```
sudo systemctl daemon-reload
```

3. Restart the service:

```
sudo systemctl restart no-more-sql
```

### Troubleshooting

1. If the app isn't accessible:

```
# Check if service is running
sudo systemctl status no-more-sql
```

2. Check for errors in logs:

```
sudo journalctl -u no-more-sql -n 50
```

3. If you see permission errors:

```
# Check file ownership
ls -l /home/porwals/GitHub/projects/no-more-sql
```

4. Check service user:

```
grep User /etc/systemd/system/no-more-sql.service
```

5. If new dependencies aren't working:

```
# Verify virtual environment
ls -l /home/porwals/GitHub/projects/no-more-sql/.venv/bin
```

6. Check Python path:

```
echo $PATH
```

7. If you see "Connection refused" errors with Ollama:

```
# Start Ollama service
sudo systemctl start ollama
```

8. Check Ollama status:

```
sudo systemctl status ollama
```

9. If needed, pull the model:

```
ollama pull llama3.1:70b
```

10. Restart the no-more-sql service:

```
sudo systemctl restart no-more-sql
```

11. Check logs:

```
sudo journalctl -u no-more-sql -f
```

### Important Paths

- Application code: /home/porwals/GitHub/projects/no-more-sql
- Service configuration: /etc/systemd/system/no-more-sql.service
- Virtual environment: /home/porwals/GitHub/projects/no-more-sql/.venv
- Database location: /home/porwals/GitHub/projects/no-more-sql/data/feedback.db

### Development Workflow

1. Make code changes in the repository
2. Test locally if needed:
    uv run streamlit run code/main.py
3. Restart the service to apply changes:
    sudo systemctl restart no-more-sql
4. Monitor logs for any issues:
    sudo journalctl -u no-more-sql -f

### Backup Considerations

- The feedback database is stored in data/feedback.db
- The FAISS index is stored in text_to_sql_index.faiss
- Consider backing up these files periodically

### Security Notes

- The service runs as user 'porwals'
- The app is accessible on port 8508
- Make sure firewall rules allow access to this port
- Consider implementing authentication if needed

### Usage (Old, for when we were doing fine-tuning)

1. poetry install
2. Run accelerate config - make sure you select
    - single node training
    - multi-gpu
    - fp16/bf16

3. Launch the train script
    accelerate launch train.py

4. Run inference script
    python inference.py

Convert csv to jsonl format:
    # update the fire command to the function you need
    python utils.py 'data/train_validation.csv' 'data/train.jsonl'
    2024-06-03 19:05:31.791 | INFO     | __main__:csv_to_jsonl:12 - Converted data/train_validation.csv to data/train.jsonl

#### Caveats
1. Use python < 3.12 (tested on 3.10)
2. To use multiple GPUs, set ddp_find_unused_parameters=False in Training Arguments.
4. Device map is created using PartialState from accelerate
5. Used prepare_model_for_kbit_training from peft

## Prerequisites

1. Ollama must be installed and running via Docker:
    ```bash
    # Start Ollama container
    docker run -d \
      --name ollama \
      --gpus all \
      -p 11434:11434 \
      -v ollama:/root/.ollama \
      ollama/ollama

    # Pull required model
    docker exec ollama ollama pull llama3.1:70b
    ```

2. CUDA-capable GPU
    - Required for running the LLM and embeddings

3. Python 3.10
    - Required packages in requirements.txt

## Docker Configuration and Model Storage

### Docker Setup

1. Docker root directory is configured in `/etc/docker/daemon.json`:
```json
{
    "data-root": "/data/docker",
    "runtimes": {
        "nvidia": {
            "args": [],
            "path": "nvidia-container-runtime"
        }
    },
    "dns": ["8.8.8.8", "8.8.4.4"],
    "dns-search": [""]
}
```

### Model Storage
1. Models are stored in Docker volume, not in container:
    - Location: `/data/docker/volumes/ollama/_data/models/`
    - Current models:
        - llama3.1:70b (42GB)
        - deepseek-r1:1.5b (1.1GB)

2. Check model status:

```bash
# List available models
docker exec ollama ollama list

# Check model storage
du -h /data/docker/volumes/ollama/_data/models/blobs

# View model details
docker exec ollama ollama show llama3.1:70b
```

### Architecture

1. Container serves models via API (port 11434)

2. Python code connects to API:

```python
import ollama
ollama.BASE_URL = "http://localhost:11434"
```

3. Models persist in Docker volume even if container is restarted

### Resource Usage
- Container memory usage: ~41GB
- Models stored in `/data` for larger storage capacity
- Container mounts volume: `-v ollama:/root/.ollama`

### Installing Models

1. Using curl commands:
```bash
# Pull llama3.1:70b model
curl -X POST http://localhost:11434/api/pull \
    -H "Content-Type: application/json" \
    -d '{"name": "llama3.1:70b"}'

# Pull deepseek-r1:1.5b model
curl -X POST http://localhost:11434/api/pull \
    -H "Content-Type: application/json" \
    -d '{"name": "deepseek-r1:1.5b"}'

# Check model download progress
curl http://localhost:11434/api/show \
    -H "Content-Type: application/json" \
    -d '{"name": "llama3.1:70b"}'
```

2. Using Docker commands (alternative):
```bash
# Pull models through Docker
docker exec ollama ollama pull llama3.1:70b
docker exec ollama ollama pull deepseek-r1:1.5b

# List installed models
docker exec ollama ollama list
```

Note: Models are large files (llama3.1:70b is 42GB), ensure sufficient disk space in `/data/docker/volumes/ollama/_data/models/`.

# To run a docker container with a particular configuration:

```bash
docker run -d \
  --name ollama \
  --gpus all \
  --runtime=nvidia \
  -e NVIDIA_VISIBLE_DEVICES=all \
  -e NVIDIA_DRIVER_CAPABILITIES=all \
  -p 11434:11434 \
  -v ollama:/root/.ollama \
  ollama/ollama

```

### Access URLs

When the service shows `URL: http://0.0.0.0:8080`, the app is accessible at:

1. From the server itself:
   ```
   http://localhost:8080
   http://127.0.0.1:8080
   ```

2. From other machines on the network:
   ```
   http://anlpa1.mskcc.org:8080
   # or
   http://140.163.26.16:8080
   ```

Note: 0.0.0.0 means the app is listening on all network interfaces. Replace with your actual server hostname or IP.
