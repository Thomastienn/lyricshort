from PIL import ImageFont

import ffmpeg


class Utils:
    """
    Utility class for common operations related to video files.
    """

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
    def get_font_dimensions(font_size, text, font_path=None):
        """
        Get the dimensions of the text when rendered with the specified font and size.
        """
        if font_path is None:
            font = ImageFont.load_default(font_size)
        else:
            font = ImageFont.truetype(font_path, font_size)

        bbox = font.getbbox(text)
        width = bbox[2] - bbox[0]
        height = bbox[3] - bbox[1]
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
