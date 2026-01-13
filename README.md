# demodata-sender

AWS Lambda function for generating demo factory telemetry and sending it to the SORACOM Unified Endpoint.

## Build `libsoratun.so` for Lambda (arm64)

Build the shared library on the same architecture as your Lambda. Example for arm64 using the Lambda Python 3.12 base image:

First time only (or after cloning): initialize submodules.

```bash
git submodule update --init --recursive
```

```bash
docker run --rm --platform linux/arm64 \
  --entrypoint "" -u root \
  -v "$PWD":/work -w /tmp public.ecr.aws/lambda/python:3.12 \
  bash -lc '
    set -e
    dnf install -y git gcc golang
    export GOTOOLCHAIN=auto
    rm -rf /tmp/libsoratun
    git clone https://github.com/0x6b/libsoratun /tmp/libsoratun
    cd /tmp/libsoratun
    go env -w GOPROXY=https://proxy.golang.org,direct
    # Optional: add JSON Content-Type header
    python - <<'"'"'PY'"'"'
from pathlib import Path
p = Path("libsoratun/client.go")
old = "headers:  []string{ua},"
new = "headers:  []string{ua, \"Content-Type: application/json\"},"
txt = p.read_text()
if old in txt:
    p.write_text(txt.replace(old, new, 1))
PY
    go mod tidy
    GOOS=linux GOARCH=arm64 CGO_ENABLED=1 \
      go build -buildmode=c-shared \
      -ldflags="-X \"github.com/0x6b/libsoratun/libsoratun.Revision=$(git rev-parse --short HEAD)\"" \
      -o /work/libsoratun.so libsoratun.go
  '
```

If your function architecture is x86_64, switch `--platform` to `linux/amd64` and set `GOARCH=amd64`.

## Configuration (.env)

`deploy.sh` reads `.env` automatically when present. Start by copying the template:

```bash
cp .env.example .env
```

Edit `.env` with your AWS profile/region/function name. Set `ROLE_ARN` only when creating a new function; leave it empty when updating an existing one.

## Deploy to Lambda

Place the following files in the project root before packaging:

- `lambda_function.py`
- `demodata_sender/`
- `libsoratun.so`
- `arc.json`

Then deploy with the helper script (defaults: profile `soracom-dev`, region `ap-northeast-1`, function name `demodata-sender`, arch `arm64`):

```bash
./deploy.sh
```

The function reads the SORACOM Arc configuration from `ARC_CONFIG_PATH` (defaults to `arc.json` in the Lambda
working directory).
