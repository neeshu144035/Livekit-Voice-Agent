import re
import sys

with open('/tmp/agent_deploy/agent.py', 'r') as f:
    content = f.read()

v3_code = '''
        # Check for v3 models - they require HTTP instead of WebSocket
        model_lower = str(selected_tts_model or '').strip().lower()
        is_v3 = 'v3' in model_lower and model_lower not in ('eleven_flash_v2_5', 'eleven_turbo_v2_5', 'eleven_multilingual_v2')
        
        if is_v3:
            try:
                from elevenlabs import ElevenLabs
                from livekit.agents import tts as tts_module
                
                eleven_client = ElevenLabs(api_key=eleven_key)
                logger.info(f'Using ElevenLabs {selected_tts_model} via HTTP (v3)')
                
                class ElevenLabsV3HTTP(tts_module.TTS):
                    def __init__(self, voice_id: str, model: str, client):
                        self._voice_id = voice_id
                        self._model = model
                        self._client = client
                        super().__init__(
                            capabilities=tts_module.TTSCapabilities(streaming=False, aligned_transcript=False),
                            sample_rate=44100, num_channels=1,
                        )
                    
                    @property
                    def identity(self):
                        return f'elevenlabs-v3:{self._voice_id}'
                    
                    def synthesize(self, text: str, conn_options=None):
                        return _ElevenLabsV3Stream(tts=self, input_text=text, conn_options=conn_options or tts_module.DEFAULT_API_CONNECT_OPTIONS)
                
                class _ElevenLabsV3Stream(tts_module.ChunkedStream):
                    def __init__(self, *, tts, input_text, conn_options):
                        super().__init__(tts=tts, input_text=input_text, conn_options=conn_options)
                        self._tts = tts
                    
                    async def _run(self, output_emitter):
                        output_emitter.initialize(sample_rate=44100, num_channels=1, mime_type='audio/mpeg')
                        audio_stream = self._tts._client.text_to_speech.stream(
                            voice_id=self._tts._voice_id, text=self._input_text, 
                            model_id=self._tts._model, output_format='mp3_44100_128',
                        )
                        audio_data = b''.join(audio_stream)
                        output_emitter.write(audio_data)
                        output_emitter.end()
                
                tts_engine = ElevenLabsV3HTTP(voice_id=selected_voice, model=selected_tts_model, client=eleven_client)
                
            except ImportError:
                logger.warning('ELEVENLABS_V3_SDK_MISSING: falling back to eleven_flash_v2_5')
                selected_tts_model = 'eleven_flash_v2_5'
                is_v3 = False
            except Exception as e:
                logger.error(f'ELEVENLABS_V3_INIT_FAILED: {e}, falling back to eleven_flash_v2_5')
                selected_tts_model = 'eleven_flash_v2_5'
                is_v3 = False
        
        if not is_v3:
'''

old_line = '        tts_engine = elevenlabs.TTS(**eleven_kwargs)'
new_code = v3_code + old_line

content = content.replace(old_line, new_code)

with open('/tmp/agent_deploy/agent.py', 'w') as f:
    f.write(content)

print('Modified successfully')