# MIB Same-Model HTTP Model Contract

The `http_json` model client deliberately uses a provider-neutral, stateless request/response contract.

## Request

```json
{
  "model": "fixed-model-id",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "..."}
  ],
  "parameters": {
    "temperature": 0,
    "max_tokens": 768,
    "seed": 123456
  },
  "request_id": "..."
}
```

## Response

```json
{
  "text": "{\"type\":\"message\",\"content\":\"...\"}",
  "usage": {
    "input_tokens": 123,
    "output_tokens": 17
  },
  "metadata": {
    "provider_request_id": "optional"
  }
}
```

The model server MUST treat each request independently. It MUST NOT retain hidden conversational state across requests or conditions.
