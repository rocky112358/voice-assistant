import json
import logging
import pathlib2 as pathlib
import os
import socket
import sys
import tempfile
import uuid
import wave

import click
import google.auth.transport.grpc
import google.auth.transport.requests
import google.oauth2.credentials
from google.assistant.embedded.v1alpha2 import (
    embedded_assistant_pb2,
    embedded_assistant_pb2_grpc
)
import pocketsphinx

from helpers import assistant_helpers, audio_helpers, device_helpers


api_endpoint = 'embeddedassistant.googleapis.com'
project_id = 'aiy-project-6fa34'
device_model_id = 'aiy-project-6fa34-sleepybear-speaker-gnilt8'
device_config = './device_config.json'
conversation_stream=None

logging.basicConfig(format="[%(levelname)s] %(asctime)s|%(filename)s:%(lineno)s|%(message)s", level="DEBUG")


def create_grpc_channel(credentials):
    try:
        with open(credentials, 'r') as f:
            credentials = google.oauth2.credentials.Credentials(token=None,
                                                                **json.load(f))
            http_request = google.auth.transport.requests.Request()
            credentials.refresh(http_request)
    except Exception as e:
        logging.error('Error loading credentials: %s', e)
        logging.error('Run google-oauthlib-tool to initialize '
                      'new OAuth 2.0 credentials.')
        sys.exit(-1)
    logging.info('Connecting to %s', api_endpoint)

    return google.auth.transport.grpc.secure_authorized_channel(
        credentials, http_request, api_endpoint)


def create_conversation_stream():
    audio_source = audio_helpers.SoundDeviceStream(
        sample_rate=audio_helpers.DEFAULT_AUDIO_SAMPLE_RATE,
        sample_width=audio_helpers.DEFAULT_AUDIO_SAMPLE_WIDTH,
        block_size=audio_helpers.DEFAULT_AUDIO_DEVICE_BLOCK_SIZE,
        flush_size=audio_helpers.DEFAULT_AUDIO_DEVICE_FLUSH_SIZE
    )
    audio_sink = audio_helpers.SoundDeviceStream(
        sample_rate=audio_helpers.DEFAULT_AUDIO_SAMPLE_RATE,
        sample_width=audio_helpers.DEFAULT_AUDIO_SAMPLE_WIDTH,
        block_size=audio_helpers.DEFAULT_AUDIO_DEVICE_BLOCK_SIZE,
        flush_size=audio_helpers.DEFAULT_AUDIO_DEVICE_FLUSH_SIZE
    )

    return audio_helpers.ConversationStream(
        source=audio_source,
        sink=audio_sink,
        iter_size=audio_helpers.DEFAULT_AUDIO_ITER_SIZE,
        sample_width=audio_helpers.DEFAULT_AUDIO_SAMPLE_WIDTH,
    )


def run_assistant(grpc_channel, conversation_stream):
    """
    device_id = str(uuid.uuid1())
    device_base_url = (
        'https://%s/v1alpha2/projects/%s/devices' % (api_endpoint,
                                                     project_id)
    )
    payload = {
        'id': device_id,
        'model_id': device_model_id,
        'client_type': 'SDK_SERVICE'
    }
    session = google.auth.transport.requests.AuthorizedSession(
        credentials
    )
    r = session.post(device_base_url, data=json.dumps(payload))
    if r.status_code != 200:
        logging.error('Failed to register device: %s', r.text)
        sys.exit(-1)

    logging.info('Device registered: %s', device_id)
    pathlib.Path(os.path.dirname(device_config)).mkdir(exist_ok=True)
    with open(device_config, 'w') as f:
        json.dump(payload, f)
    """

    with open("./device_config.json") as f:
        device_config = json.load(f)
    device_handler = device_helpers.DeviceRequestHandler(device_config['id'])

    @device_handler.command('com.example.commands.WakeupDesktop')
    def wake_on_lan(**kwargs):
        print("Sending magic packet...")
        magic = bytes.fromhex("FF"*6 + "2CF05DEA0A98"*16)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # UDP
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)  # Broadcast
        sock.sendto(magic, ("192.168.0.255", 7))  # to port 7 of broadcast address

    assistant = embedded_assistant_pb2_grpc.EmbeddedAssistantStub(
        grpc_channel
    )
    conversation_state = None
    is_new_conversation = True
    def gen_assist_requests():
        config = embedded_assistant_pb2.AssistConfig(
            audio_in_config=embedded_assistant_pb2.AudioInConfig(
                encoding='LINEAR16',
                sample_rate_hertz=conversation_stream.sample_rate,
            ),
            audio_out_config=embedded_assistant_pb2.AudioOutConfig(
                encoding='LINEAR16',
                sample_rate_hertz=conversation_stream.sample_rate,
                volume_percentage=conversation_stream.volume_percentage,
            ),
            dialog_state_in=embedded_assistant_pb2.DialogStateIn(
                language_code='ko-KR',
                conversation_state=conversation_state,
                is_new_conversation=is_new_conversation,
            ),
            device_config=embedded_assistant_pb2.DeviceConfig(
                device_id=device_config['id'],
                device_model_id=device_config['model_id'],
            )
        )
        yield embedded_assistant_pb2.AssistRequest(config=config)
        for data in conversation_stream:
            yield embedded_assistant_pb2.AssistRequest(audio_in=data)

    def iter_log_assist_requests():
        for c in gen_assist_requests():
            # assistant_helpers.log_assist_request_without_audio(c)
            yield c
        logging.debug('Reached end of AssistRequest iteration.')

    # setup hotword decoder
    config = pocketsphinx.Decoder.default_config()
    (fd, dict_name) = tempfile.mkstemp()
    with os.fdopen(fd, 'w') as f:
        f.write("hey HH EY\n")
        f.write("patrasche P AH T R AA SH UW\n")
        f.write("uni Y UW N IY\n")
    config.set_string('-hmm', os.path.join(pocketsphinx.get_model_path(), 'en-us'))
    config.set_string('-dict', dict_name)
    config.set_string('-keyphrase', 'hey uni')
    config.set_float('-kws_threshold', float(1e-20))
    config.set_float('-samprate', 16000)
    config.set_int('-nfft', 4096)
    config.set_string('-logfn', '/dev/null')
    hotword_decoder = pocketsphinx.Decoder(config)
    
    with wave.open("./sfx/command_start.wav", "rb") as f:  
        command_start_sound_data = f.readframes(f.getnframes())
        command_start_sound_data = command_start_sound_data[::f.getframerate()//8192]  # downsample wav file into framerate of 8192
    with wave.open("./sfx/command_end.wav", "rb") as f:  
        command_end_sound_data = f.readframes(f.getnframes())
        command_end_sound_data = command_end_sound_data[::f.getframerate()//8192]  # downsample wav file into framerate of 8192
    while True:
        # wait for the hotword
        conversation_stream.start_recording()
        hotword_decoder.start_utt()
        for data in conversation_stream:
            hotword_decoder.process_raw(data, False, False)
            if hotword_decoder.hyp():
                hotword_decoder.end_utt()
                break
        conversation_stream.stop_recording()
        
        logging.info('Hotword detected.')

        # play sound
        conversation_stream.start_playback()
        for block in [command_start_sound_data[x:x+8192] for x in range(0, len(command_start_sound_data), 8192)]:
            conversation_stream.write(block)
        conversation_stream.stop_playback()

        # listen to the request
        logging.info('Listening...')
        conversation_stream.start_recording()
        for resp in assistant.Assist(iter_log_assist_requests(), 60*3+5):
            # assistant_helpers.log_assist_response_without_audio(resp)
            if resp.event_type == embedded_assistant_pb2.AssistResponse.END_OF_UTTERANCE:
                logging.info('End of audio request detected.')
                logging.info('Stopping recording.')
                conversation_stream.stop_recording()
            if resp.speech_results:
                logging.info('Transcript of user request: "%s".',
                             ' '.join(r.transcript
                                      for r in resp.speech_results))
            if len(resp.audio_out.audio_data) > 0:
                if not conversation_stream.playing:
                    conversation_stream.stop_recording()

                    # play sound
                    conversation_stream.start_playback()
                    for block in [command_end_sound_data[x:x+8192] for x in range(0, len(command_end_sound_data), 8192)]:
                        conversation_stream.write(block)
                    conversation_stream.stop_playback()

                    conversation_stream.start_playback()
                    logging.info('Playing assistant response.')
                conversation_stream.write(resp.audio_out.audio_data)
            if resp.dialog_state_out.conversation_state:
                conversation_state = resp.dialog_state_out.conversation_state
                logging.debug('Updating conversation state.')
            if resp.device_action.device_request_json:
                device_request = json.loads(
                    resp.device_action.device_request_json
                )
                device_handler(device_request)
        conversation_stream.stop_playback()


if __name__=="__main__":
    credential_filename = "./credentials.json"

    grpc_channel = create_grpc_channel(credential_filename)
    conversation_stream = create_conversation_stream()

    run_assistant(grpc_channel, conversation_stream)
