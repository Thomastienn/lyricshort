import os
import glob
import platform
import random

from PIL import ImageFont

import ffmpeg


class StreamUtils:
    """
    Utility class for common operations related to video files.
    """

    @staticmethod
    def convert_to_wav(file_path):
        """
        Convert a video file to WAV format.
        Returns the path to the converted WAV file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File '{file_path}' does not exist.")

        output_file = os.path.splitext(file_path)[0] + ".wav"
        ffmpeg.input(file_path).output(output_file, format="wav").run(
            overwrite_output=True, quiet=True
        )
        return output_file

    @staticmethod
    def get_video_dimensions(file_path):
        """
        Get the dimensions of a video file.
        Returns a tuple (width, height).
        """
        probe = ffmpeg.probe(file_path)
        video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
        width = video_stream["width"]
        height = video_stream["height"]
        return width, height

    @staticmethod
    def get_start_time(file_path):
        """
        Get the start time of the first video stream in a given file.
        """
        probe = ffmpeg.probe(file_path)
        # Usually the first video stream
        video_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
        # start_time is a string like "0.000000"
        start_time = float(video_stream.get("start_time", 0))
        return start_time

    @staticmethod
    def get_video_codec(file_path):
        """
        Get the video codec of a given file.
        """
        probe = ffmpeg.probe(file_path)
        for stream in probe["streams"]:
            if stream["codec_type"] == "video":
                return stream["codec_name"]
        return None

    @staticmethod
    def get_audio_codec(file_path):
        """
        Get the audio codec of a given file.
        """
        probe = ffmpeg.probe(file_path)
        for stream in probe["streams"]:
            if stream["codec_type"] == "audio":
                return stream["codec_name"]
        return None


class FontUtils:
    """
    Utility class for common operations related to fonts.
    """

    _CURRENT_FONT: str | None = None

    @staticmethod
    def find_all_fonts():
        """
        Get all the fonts in the fonts/static directory.
        """
        fonts_dir = "fonts/static"
        if not os.path.exists(fonts_dir):
            raise FileNotFoundError(f"Fonts directory '{fonts_dir}' does not exist.")

        # Use glob to find all font files in the directory
        font_files = glob.glob(os.path.join(fonts_dir, "*.*"))
        # Filter out non-font files based on common font extensions
        font_extensions = {".ttf", ".otf", ".woff", ".woff2", ".ttc"}
        return [
            f for f in font_files if os.path.splitext(f)[1].lower() in font_extensions
        ]

    # Basename: path (e.g., "Arial.ttf") -> full path (e.g., "/usr/share/fonts/Arial.ttf")
    @staticmethod
    def all_fonts() -> dict[str, str]:
        """
        Get all the fonts in the fonts/ directory.
        Returns a dictionary where keys are font names and values are full paths.
        """
        return {os.path.basename(font): font for font in FontUtils.find_all_fonts()}

    @staticmethod
    def get_current_font() -> str:
        """
        Get a random font from the available fonts.
        """
        if FontUtils._CURRENT_FONT is not None:
            return FontUtils._CURRENT_FONT

        # selected_font = random.choice(list(FontUtils.all_fonts().values()))
        selected_font = None
        for font in FontUtils.all_fonts().values():
            base_name = os.path.basename(font)
            if base_name.lower().startswith("noto"):
                selected_font = font
                break
        if selected_font is None:
            selected_font = random.choice(list(FontUtils.all_fonts().values()))
        FontUtils._CURRENT_FONT = selected_font

        return selected_font

    # CURRENT_FONT: str = random.choice(list(FONTS_AVAILABLE.values()))

    @staticmethod
    def get_font_dimensions(font_size, text, font_path=None):
        """
        Get the dimensions of the text when rendered with the specified font and size.
        """
        if font_path is None:
            font = ImageFont.truetype(FontUtils.get_current_font(), font_size)
        else:
            font = ImageFont.truetype(font_path, font_size)

        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
        return width, height


if __name__ == "__main__":
    print(FontUtils.get_current_font())
