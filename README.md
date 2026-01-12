# demodata-sender

AWS Lambda function for generating demo factory telemetry and sending it to the SORACOM Unified Endpoint.

## Usage (AWS Lambda)

1. Build `libsoratun.so` on the target Lambda runtime (arm64 recommended) by following the instructions in the
   [libsoratun repository](https://github.com/0x6b/libsoratun).
2. Place the following files in the same directory before packaging:

   - `lambda_function.py`
   - `demodata_sender/`
   - `libsoratun.so`
   - `arc.json`

3. Package and deploy to Lambda:

```bash
zip -r lambda.zip lambda_function.py demodata_sender libsoratun.so arc.json
```

The function reads the SORACOM Arc configuration from `ARC_CONFIG_PATH` (defaults to `arc.json` in the Lambda
working directory).
