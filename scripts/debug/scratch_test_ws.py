import asyncio
import os
import aiohttp

async def test_ws(url_suffix):
    api_key = os.environ.get("ELEVEN_API_KEY", "")
    url = f'wss://api.elevenlabs.io/v1/text-to-speech/pNInz6obpgDQGcFmaJgB/stream-input?{url_suffix}'
    headers = {"xi-api-key": api_key}
    async with aiohttp.ClientSession() as session:
        try:
            async with session.ws_connect(url, headers=headers) as ws:
                return "SUCCESS"
        except aiohttp.client_exceptions.WSServerHandshakeError as e:
            return f"FAIL: {e.status} - {e.message}"
        except Exception as e:
            return f"ERROR: {type(e)}"

async def main():
    queries = [
        "model_id=eleven_v3",
        "model_id=eleven_v3&output_format=pcm_16000",
        "model_id=eleven_flash_v2_5&output_format=mp3_22050_32",
        "model_id=eleven_multilingual_v2",
        "model_id=eleven_v3&output_format=mp3_22050_32",
        "model_id=eleven_v3&enable_ssml_parsing=true",
    ]
    for q in queries:
        print(f"Testing {q} ...")
        res = await test_ws(q)
        print(f"  Result: {res}")

asyncio.run(main())
