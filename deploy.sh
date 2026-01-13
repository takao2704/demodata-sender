#!/usr/bin/env bash
# Helper script to package and deploy the Lambda. It expects libsoratun.so and arc.json
# to be present alongside lambda_function.py.

set -euo pipefail

# Load environment overrides from .env if present
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  source .env
  set +a
fi

PROFILE="${PROFILE:-soracom-dev}"
REGION="${REGION:-ap-northeast-1}"
FUNCTION_NAME="${FUNCTION_NAME:-demodata-sender}"
ZIP_FILE="${ZIP_FILE:-lambda.zip}"
RUNTIME="${RUNTIME:-python3.12}"
ARCHITECTURE="${ARCHITECTURE:-arm64}"
ROLE_ARN="${ROLE_ARN:-}"

required_files=("lambda_function.py" "demodata_sender" "libsoratun.so" "arc.json")
for f in "${required_files[@]}"; do
  if [[ ! -e "$f" ]]; then
    echo "Missing required file: $f" >&2
    exit 1
  fi
done

echo "Packaging Lambda into $ZIP_FILE ..."
rm -f "$ZIP_FILE"
zip -r "$ZIP_FILE" lambda_function.py demodata_sender libsoratun.so arc.json >/dev/null

if aws lambda get-function \
  --function-name "$FUNCTION_NAME" \
  --region "$REGION" \
  --profile "$PROFILE" >/dev/null 2>&1; then
  echo "Updating existing function code ($FUNCTION_NAME)..."
  aws lambda update-function-code \
    --function-name "$FUNCTION_NAME" \
    --zip-file "fileb://$ZIP_FILE" \
    --region "$REGION" \
    --profile "$PROFILE"
else
  if [[ -z "$ROLE_ARN" ]]; then
    echo "ROLE_ARN is required to create a new Lambda function." >&2
    exit 1
  fi
  echo "Creating new function ($FUNCTION_NAME)..."
  aws lambda create-function \
    --function-name "$FUNCTION_NAME" \
    --runtime "$RUNTIME" \
    --handler "lambda_function.lambda_handler" \
    --zip-file "fileb://$ZIP_FILE" \
    --role "$ROLE_ARN" \
    --architectures "$ARCHITECTURE" \
    --timeout 30 \
    --memory-size 256 \
    --region "$REGION" \
    --profile "$PROFILE"
fi

echo "Done. Deployed $FUNCTION_NAME to $REGION using profile $PROFILE."
