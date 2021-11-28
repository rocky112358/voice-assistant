## Installation Instructions (Documentation work in progess...)

Ubuntu 20.04.2

```sh
sudo apt update
sudo apt install swig libasound2-dev libpulse-dev libportaudio2
python -m pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

google-oauthlib-tool --scope https://www.googleapis.com/auth/assistant-sdk-prototype \
      --save --headless --client-secrets ./<your-client-secret-file>.json
ln -s ~/.config/google-oauthlib-tool/credentials.json

# config your audio device
vi ~/.asoundrc
# copy and paste, then modify

# pcm.!default {
#    type asym
#    capture.pcm "mic"
#    playback.pcm "speaker"
# }
# pcm.mic {
#   type plug
#   slave {
#     pcm "hw:1,0"  # find card number, device number from the command output: $ arecord -l
#   }
# }
# pcm.speaker {
#   type plug
#   slave {
#     pcm "hw:0,0"  # find card number, device number from the command output: $ aplay -l
#   }
# }

# adjust volume with commands below
alsamixer  # adjust volume
speaker-test -t wav  # play test script

# test microphone with commands below
alsamixer  # adjust volume, press [F6] for swtiching card
arecord --format=S16_LE --duration=5 --rate=16000 --file-type=raw out.raw  # record
aplay --format=S16_LE --rate=16000 out.raw  # play

...

python app.py
```
