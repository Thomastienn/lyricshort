import librosa
import soundfile as sf

from utils import StreamUtils
from google import genai
from google.genai import types
from dotenv import load_dotenv

from structures import Chorus

load_dotenv()


class SoundAnalyzer:
    def __init__(self, path: str):
        self.path = path
        if not path.endswith(".wav"):
            self.path = StreamUtils.convert_to_wav(path)

    def _get_features(self):
        y, sr = sf.read(self.path, always_2d=False)
        if y.ndim > 1:
            y = y.mean(axis=1)  # convert to mono manually if needed

        # Chop into 1-second chunks
        chunk_size = sr  # 1 sec = 44100 samples

        features = []
        for i in range(0, len(y), chunk_size):
            y_chunk = y[i : i + chunk_size]

            if len(y_chunk) < chunk_size:
                break  # skip last partial second

            # ── Extract features (non-deprecated, preferred usage)
            chroma = librosa.feature.chroma_stft(y=y_chunk, sr=sr).mean(
                axis=1
            )  # shape: (12,)
            mfccs = librosa.feature.mfcc(y=y_chunk, sr=sr, n_mfcc=13).mean(
                axis=1
            )  # shape: (13,)
            zcr = librosa.feature.zero_crossing_rate(y_chunk).mean()  # scalar
            rms = librosa.feature.rms(y=y_chunk).mean()  # scalar
            f0 = librosa.yin(
                y_chunk,
                fmin=float(librosa.note_to_hz("C2")),
                fmax=float(librosa.note_to_hz("C7")),
                sr=sr,
            ).mean()  # scalar

            features.append(
                {
                    "second": i // chunk_size,
                    "mfcc": mfccs.tolist(),
                    "chroma": chroma.tolist(),
                    "zcr": float(zcr),
                    "rms": float(rms),
                    "pitch": float(f0),
                }
            )
        return features

    def pick_chorus(self, lyrics_path: str):
        """
        This method should analyze the features and return the most likely chorus segment.
        """
        client = genai.Client()
        features = self._get_features()
        with open(lyrics_path, "r", encoding="utf-8") as f:
            lyrics = f.read()
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                "Here is the audio features extracted from the song:\n\n"
                + str(features)
                + "Here are the lyrics of the song: \n\n"
                + lyrics
            ],
            config=types.GenerateContentConfig(
                temperature=0.0,
                system_instruction="You are an expert in audio analysis, music productor, and sound engineer. Your task is to analyze the audio features and lyrics to identify the chorus segment of a song.",
                response_mime_type="application/json",
                response_schema=Chorus,
            ),
        )
        llm_response = response.parsed
        assert isinstance(llm_response, Chorus), "LLM response is not of type Chorus"

        return llm_response.start_time, llm_response.end_time


def _test():
    a = SoundAnalyzer("sample/sample.mp4")
    a._get_features()


if __name__ == "__main__":
    _test()
