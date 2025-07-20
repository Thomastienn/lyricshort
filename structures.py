import os
import tempfile
from enum import Enum
from abc import ABC, abstractmethod
from typing import Literal

import ffmpeg
from pydantic import BaseModel

from utils import Utils


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

    @abstractmethod
    def apply(self, file_path: str): ...


class BlurEffect(Effect):
    """
    Represents a blur effect.
    """

    radius: float = 5.0  # Default radius for the blur effect

    def apply(self, file_path: str):
        """
        Apply the blur effect to the video file.
        :param file_path: Path to the input video file
        """
        input_stream = ffmpeg.input(file_path)
        video_node = input_stream.video.filter("gblur", sigma=self.radius)
        audio_node = input_stream.audio

        audio_codec = Utils.get_audio_codec(file_path)
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
                    "-hide_banner",
                    "-loglevel",
                    "error",  # Suppress ffmpeg output
                    "-stats",  # Show progress stats
                )
                .run()
            )
            os.replace(temp_file.name, file_path)


class TextPosition(BaseModel):
    vertical: Literal["top", "center", "bottom"]
    horizontal: Literal["left", "center", "right"]


class TextOverlayEffect(Effect):
    """
    Represents a text overlay effect.
    """

    text: str
    position: (
        tuple[int, int] | TextPosition
    )  # Position as (x, y) coordinates or TextPosition
    font_size: int = 12  # Default font size
    color: str = "black"  # Default color for the text overlay
    background_color: str = "0x00000000"  # Default transparent background color
    start_time: float | None = None  # Start time in seconds for the text overlay
    duration: int = 3  # Duration in seconds for which the text is displayed

    def apply(self, file_path: str):
        """
        Apply the text overlay effect to the video file.
        :param file_path: Path to the input video file
        """
        audio_codec = Utils.get_audio_codec(file_path)
        acodec = "copy" if audio_codec == "aac" else "aac"

        input_stream = ffmpeg.input(file_path)
        if self.start_time is None:
            start_time = Utils.get_start_time(file_path) or 0
        else:
            start_time = self.start_time

        width, height = Utils.get_video_dimensions(file_path)
        font_width, font_height = Utils.get_font_dimensions(self.font_size, self.text)

        if isinstance(self.position, TextPosition):
            match self.position.horizontal:
                case "left":
                    x = 0
                case "center":
                    x = (width - font_width) / 2
                case "right":
                    x = width - font_width
            match self.position.vertical:
                case "top":
                    y = 0
                case "center":
                    y = (height - font_height) / 2
                case "bottom":
                    y = height - font_height
        else:
            x = self.position[0]
            y = self.position[1]

        video_node = input_stream.video.filter(
            "drawtext",
            text=self.text,
            x=x,
            y=y,
            fontsize=self.font_size,
            fontcolor=self.color,
            box=1,
            boxcolor=self.background_color,
            enable=f"between(t,{start_time},{start_time + self.duration})",
        )

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
                    "-hide_banner",
                    "-loglevel",
                    "error",  # Suppress ffmpeg output
                    "-stats",  # Show progress stats
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

    def apply(self, file_path: str):
        """
        Apply the trim effect to the video file.
        :param file_path: Path to the input video file
        """
        audio_codec = Utils.get_audio_codec(file_path)
        acodec = "copy" if audio_codec == "aac" else "aac"

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            (
                ffmpeg.input(file_path, ss=self.start_time, to=self.end_time)
                .output(temp_file.name, vcodec="copy", acodec=acodec)
                .overwrite_output()
                .global_args(
                    "-hide_banner",
                    "-loglevel",
                    "error",  # Suppress ffmpeg output
                    "-stats",  # Show progress stats
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

    def apply(self, file_path: str):
        """
        Apply the fill overlay effect to the video file.
        :param file_path: Path to the input video file
        """
        width, height = Utils.get_video_dimensions(file_path)

        # Streams
        input_stream = ffmpeg.input(file_path)
        video_node = input_stream.video
        audio_node = input_stream.audio

        overlay_node = (
            ffmpeg.input(
                f"color={self.color}:s={width}x{height}:d=0.1",
                f="lavfi",
            )
            .filter("format", "rgba")
            .filter("colorchannelmixer", aa=self.opacity)
        )

        video_filter = video_node.filter("format", "rgba").overlay(
            overlay_node, x=0, y=0, eof_action="repeat"
        )

        audio_codec = Utils.get_audio_codec(file_path)
        acodec = "copy" if audio_codec == "aac" else "aac"

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            (
                ffmpeg.output(
                    video_filter,
                    audio_node,
                    temp_file.name,
                    vcodec="libx264",
                    acodec=acodec,
                    pix_fmt="yuv420p",
                )
                .overwrite_output()
                .global_args(
                    "-hide_banner",
                    "-loglevel",
                    "error",  # Suppress ffmpeg output
                    "-stats",  # Show progress stats
                )
                .run()
            )
            os.replace(temp_file.name, file_path)
