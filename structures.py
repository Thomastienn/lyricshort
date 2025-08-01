import os
import tempfile
from enum import Enum
from abc import ABC, abstractmethod
from typing import Literal, ClassVar

import ffmpeg
from pydantic import BaseModel

from utils import StreamUtils, FontUtils
from logger import MyLogger


class Segment(BaseModel):
    """
    Represents a segment of a video.
    """

    start_time: float  # Start time in seconds
    end_time: float  # End time in seconds


class Verse(Segment):
    """
    Represents a verse in a video.
    """

    ...


class Chorus(Segment):
    """
    Represents a chorus in a video.
    """

    ...


class UserPrompts(BaseModel):
    """
    Represents user prompts for video editing.
    """

    title: str
    author: str
    language: str


class EffectType(Enum):
    """
    Enum representing different types of effects.
    """

    BLUR = "blur"
    TEXT_OVERLAY = "text_overlay"


class Effect(BaseModel, ABC):
    """
    A base class for all effects.
    """

    GLOBAL_ARGS: ClassVar[list[str]] = [
        "-hide_banner",
        "-loglevel",
        "error",  # Suppress ffmpeg output
        "-stats",  # Show progress stats
    ]

    def __init_subclass__(cls):
        """
        Automatically log the application of the effect when a subclass is created.
        """
        super().__init_subclass__()
        original_apply = cls.apply
        setattr(cls, "apply", MyLogger.log_apply(original_apply))

    @abstractmethod
    def apply(self, file_path: str):
        """
        Apply the effect to the video file.
        :param file_path: Path to the input video file
        """
        ...

    @abstractmethod
    def video_node(
        self, input_stream: ffmpeg.nodes.FilterableStream, *args, **kwargs
    ) -> ffmpeg.nodes.FilterableStream:
        """
        Apply the effect to the video filter node.
        :param input_stream: Input stream from ffmpeg
        :return: Filtered video node
        """
        ...


class BlurEffect(Effect):
    """
    Represents a blur effect.
    """

    radius: float = 5.0  # Default radius for the blur effect

    def video_node(
        self, input_stream_video: ffmpeg.nodes.FilterableStream, *args, **kwargs
    ):
        return input_stream_video.filter("gblur", sigma=self.radius)  # type: ignore[reportAttributeAccessIssue]

    def apply(self, file_path: str):
        """
        Apply the blur effect to the video file.
        :param file_path: Path to the input video file
        """
        input_stream = ffmpeg.input(file_path)
        video_node = self.video_node(input_stream.video)
        audio_node = input_stream.audio

        audio_codec = StreamUtils.get_audio_codec(file_path)
        acodec = "copy" if audio_codec == "aac" else "aac"

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            (
                ffmpeg.output(
                    video_node,
                    audio_node,
                    temp_file.name,
                    vcodec="libx264",
                    acodec=acodec,
                )
                .overwrite_output()
                .global_args(
                    *self.GLOBAL_ARGS  # Use global arguments for ffmpeg
                )
                .run()
            )
            os.replace(temp_file.name, file_path)


class TextPosition(BaseModel):
    vertical: Literal["top", "center", "bottom"]
    horizontal: Literal["left", "center", "right"]


class TextOverlayProperties(BaseModel):
    text: str
    position: (
        tuple[int, int] | TextPosition
    )  # Position as (x, y) coordinates or TextPosition
    font_size: int = 12  # Default font size
    color: str = "black"  # Default color for the text overlay
    background_color: str = "0x00000000"  # Default transparent background color
    start_time: float | None = None  # Start time in seconds for the text overlay
    duration: int = 3  # Duration in seconds for which the text is displayed

    offset: tuple[int, int] = (
        0,
        0,
    )  # Offset for the text overlay (move right, move down) in pixels


class TextOverlayEffect(Effect):
    """
    Represents a text overlay effect.
    """

    texts: list[TextOverlayProperties]

    _temp_files: list[str] = []  # List to keep track of temporary files created

    def video_node(
        self, input_stream_video: ffmpeg.nodes.FilterableStream, *args, **kwargs
    ):
        file_path = args[0] if args else kwargs.get("file_path", None)
        if not file_path:
            raise ValueError("File path must be provided for video node processing.")
        video_node = input_stream_video
        for text_props in self.texts:
            if text_props.start_time is None:
                start_time = StreamUtils.get_start_time(file_path) or 0
            else:
                start_time = text_props.start_time

            width, height = StreamUtils.get_video_dimensions(file_path)
            font_width, font_height = FontUtils.get_font_dimensions(
                text_props.font_size, text_props.text
            )

            if isinstance(text_props.position, TextPosition):
                match text_props.position.horizontal:
                    case "left":
                        x = 0
                    case "center":
                        x = (width - font_width) / 2
                    case "right":
                        x = width - font_width
                match text_props.position.vertical:
                    case "top":
                        y = 0
                    case "center":
                        y = (height - font_height) / 2
                    case "bottom":
                        y = height - font_height
            else:
                x = text_props.position[0]
                y = text_props.position[1]

            x += text_props.offset[0]  # Move right
            y += text_props.offset[1]  # Move down

            extra_args = {}
            if FontUtils._CURRENT_FONT is not None:
                extra_args["fontfile"] = FontUtils._CURRENT_FONT

            video_node = video_node.filter(  # type: ignore[reportAttributeAccessIssue]
                "drawtext",
                text=text_props.text,
                x=x,
                y=y,
                fontsize=text_props.font_size,
                fontcolor=text_props.color,
                box=1,
                boxcolor=text_props.background_color,
                enable=f"between(t,{start_time},{start_time + text_props.duration})",
                **extra_args,
            )

        return video_node

    def apply(self, file_path: str):
        """
        Apply the text overlay effect to the video file.
        :param file_path: Path to the input video file
        """
        audio_codec = StreamUtils.get_audio_codec(file_path)
        acodec = "copy" if audio_codec == "aac" else "aac"

        input_stream = ffmpeg.input(file_path)
        video_node = self.video_node(input_stream.video, file_path)
        audio_node = input_stream.audio

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            # Use ffmpeg to add text overlay
            (
                ffmpeg.output(
                    video_node,
                    audio_node,
                    temp_file.name,
                    vcodec="libx264",
                    acodec=acodec,
                )
                .overwrite_output()
                .global_args(
                    *self.GLOBAL_ARGS  # Use global arguments for ffmpeg
                )
                .run()
            )
            os.replace(temp_file.name, file_path)


class TrimEffect(Effect):
    """
    Represents a trim effect.
    """

    start_time: float  # Start time in seconds
    end_time: float  # End time in seconds

    def video_node(
        self, input_stream_video: ffmpeg.nodes.FilterableStream, *args, **kwargs
    ):
        return input_stream_video

    # Trim effect only apply alone
    def apply(self, file_path: str):
        """
        Apply the trim effect to the video file.
        :param file_path: Path to the input video file
        """
        audio_codec = StreamUtils.get_audio_codec(file_path)
        acodec = "copy" if audio_codec == "aac" else "aac"

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            (
                ffmpeg.input(file_path, ss=self.start_time, to=self.end_time)
                .output(temp_file.name, vcodec="copy", acodec=acodec)
                .overwrite_output()
                .global_args(
                    *self.GLOBAL_ARGS  # Use global arguments for ffmpeg
                )
                .run()
            )
            os.replace(temp_file.name, file_path)


class FillOverlayEffect(Effect):
    """
    Represents a fill overlay effect.
    """

    color: str  # Color for the fill overlay
    opacity: float = 0.5  # Opacity of the fill overlay

    def video_node(
        self, input_stream_video: ffmpeg.nodes.FilterableStream, *args, **kwargs
    ):
        file_path = args[0] if args else kwargs.get("file_path", None)
        if not file_path:
            raise ValueError("File path must be provided for video node processing.")
        width, height = StreamUtils.get_video_dimensions(file_path)
        video_node = input_stream_video
        overlay_node = (
            ffmpeg.input(
                f"color={self.color}:s={width}x{height}:d=0.1",
                f="lavfi",
            )
            .filter("format", "rgba")
            .filter("colorchannelmixer", aa=self.opacity)
        )

        video_filter = video_node.filter("format", "rgba").overlay(  # type: ignore[reportAttributeAccessIssue]
            overlay_node, x=0, y=0, eof_action="repeat"
        )
        return video_filter

    def apply(self, file_path: str):
        """
        Apply the fill overlay effect to the video file.
        :param file_path: Path to the input video file
        """

        # Streams
        input_stream = ffmpeg.input(file_path)
        video_node = self.video_node(input_stream.video, file_path)
        audio_node = input_stream.audio

        audio_codec = StreamUtils.get_audio_codec(file_path)
        acodec = "copy" if audio_codec == "aac" else "aac"

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            (
                ffmpeg.output(
                    video_node,
                    audio_node,
                    temp_file.name,
                    vcodec="libx264",
                    acodec=acodec,
                    pix_fmt="yuv420p",
                )
                .overwrite_output()
                .global_args(
                    *self.GLOBAL_ARGS  # Use global arguments for ffmpeg
                )
                .run()
            )
            os.replace(temp_file.name, file_path)
