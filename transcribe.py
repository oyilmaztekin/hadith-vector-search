import ffmpeg
import os
import json
import re
import subprocess

#  ffmpeg -i ~/Documents/records/ezkar4.m4a -ac 1 -ar 16000 -c:a pcm_s16le ~/Documents/records/ezkar4.wav


def extract_audio(video_path, output_wav_path):
    (
        ffmpeg
        .input(video_path)
        .output(output_wav_path, ac=1, ar=16000, format='wav')
        .run(overwrite_output=True)
    )

def transcribe_with_cli(wav_path):
    whisper_cli_path = "./whisper-cli.cpp/build/bin/whisper-cli"  # Adjust path as needed
    model_path = "whisper-cli.cpp/models/ggml-large-v3.bin"

    command = [
        whisper_cli_path,
        "-m", model_path,
        "-f", wav_path,
        "--language", "auto",
        "-oj",
        "--best-of", "7",
        "--beam-size", "7"
    ]
    # ./build/bin/whisper-cli -m models/ggml-large-v3.bin -f ~/Documents/records/ezkar4.wav --language tr -oj --best-of 6 --beam-size 6  
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print("Whisper CLI error:", result.stderr)
        raise RuntimeError("Whisper CLI process failed")

    if not result.stdout.strip():
        raise ValueError("No output from Whisper CLI")
    return json.loads(result.stdout)

def save_transcription(result, transcription_path):
    with open(transcription_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

def tag_languages_in_text(segments):
    arabic_pattern = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]+')
    result = []
    for seg in segments:
        text = seg['text'].strip()
        if not text:
            continue
        if arabic_pattern.search(text):
            lang = 'ar'
        else:
            lang = 'tr'
        result.append({
            'start': seg['start'],
            'end': seg['end'],
            'text': text,
            'language': lang
        })
    return result

def process_video(video_path):
    output_wav_path = "audio.wav"
    transcription_path = "transcription.json"
    tagged_sentences_path = "tagged_sentences.json"

    extract_audio(video_path, output_wav_path)
    transcription = transcribe_with_cli(output_wav_path)
    save_transcription(transcription, transcription_path)

    tagged_sentences = tag_languages_in_text(transcription['segments'])
    with open(tagged_sentences_path, 'w', encoding='utf-8') as f:
        json.dump(tagged_sentences, f, ensure_ascii=False, indent=2)

    os.remove(output_wav_path)

    print("✅ Transcription saved to transcription.json")
    print("✅ Language-tagged sentences saved to tagged_sentences.json")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Transcribe video and tag languages")
    parser.add_argument("video_path", help="Path to the video file")
    args = parser.parse_args()

    process_video(args.video_path)
