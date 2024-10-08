import asyncio
import os
import json
from azure.cognitiveservices.speech import SpeechConfig, SpeechSynthesizer, SpeechSynthesisResult, ResultReason
import socketio

# Azure Speech SDK configuration
SPEECH_KEY = os.getenv("SPEECH_KEY")
SPEECH_REGION = os.getenv("SPEECH_REGION")

# Socket.IO client setup
sio = socketio.AsyncClient()

# Texts to be synthesized
texts = [
    "Hello, how are you?",
    "I am fine, thank you."
]

# Function to connect to the Socket.IO server
async def connect_socket():
    try:
        await sio.connect('http://localhost:3000', socketio_path='/api/socket')
        print('Connected to the Socket.IO server')
    except Exception as e:
        print(f"Failed to connect to the Socket.IO server: {e}")

# Function to handle visemes and synthesize speech
async def synthesize_speech():
    try:
        # Configure speech
        speech_config = SpeechConfig(subscription=SPEECH_KEY, region=SPEECH_REGION)

        # Set up the speech synthesizer
        synthesizer = SpeechSynthesizer(speech_config=speech_config, audio_config=None)
        visemes = []
        blend_shapes_3d = []

        def viseme_callback(evt):
            visemes.append([evt.audio_offset / 10000, evt.viseme_id])
            if evt.animation:
                try:
                    # Check if evt.animation is a string and parse it if needed
                    if isinstance(evt.animation, str):
                        animation_data = json.loads(evt.animation)  # Parse JSON string into dictionary
                    elif isinstance(evt.animation, dict):
                        animation_data = evt.animation  # Already a dictionary
                    else:
                        raise ValueError("Unexpected type for evt.animation")
                    
                    blend_shapes_3d.append(animation_data)
                except (json.JSONDecodeError, ValueError) as e:
                    print(f"Error parsing animation data: {e}")

        synthesizer.viseme_received.connect(viseme_callback)

        # Generate visemes from text
        for text in texts:
            ssml = f"""
            <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang="en-US">
            <voice name="en-US-AvaNeural">
                <mstts:viseme type="FacialExpression"/>
                {text}
            </voice>
            </speak>
            """

            result: SpeechSynthesisResult = synthesizer.speak_ssml_async(ssml).get()

            if result.reason == ResultReason.SynthesizingAudioCompleted:
                # Prepare the visemes data
                response_data = {
                    "text": text,
                    "visemes": visemes,
                    "3d_blend_shapes": blend_shapes_3d
                }

                # Emit the visemes data to the Socket.IO server
                await sio.emit('message', json.dumps(response_data))

                visemes.clear()  # Clear visemes for the next text
                blend_shapes_3d.clear()  # Clear blend shapes for the next text
            else:
                print(f"Speech synthesis failed with reason: {result.reason}")

            # Delay between texts (if needed)
            await asyncio.sleep(5)  # Adjust delay as needed

    except Exception as e:
        print(f"Error: {e}")

# Main entry point
async def main():
    # Connect to the Socket.IO server
    await connect_socket()
    
    # Run the speech synthesis
    await synthesize_speech()

    # Disconnect from the server
    await asyncio.sleep(5)  # Wait for the last message to be sent
    await sio.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
