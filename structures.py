import os
import tempfile
from enum import Enum
from abc import ABC, abstractmethod

import ffmpeg
from pydantic import BaseModel


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
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            (
                ffmpeg.input(file_path)
                .filter("gblur", sigma=self.radius)
                .output(temp_file.name, vcodec="libx264", acodec="copy")
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


class TextOverlayEffect(Effect):
    """
    Represents a text overlay effect.
    """

    text: str
    position: tuple[int, int]  # Position as (x, y) coordinates
    font_size: int = 12  # Default font size
    color: str = "black"  # Default color for the text overlay
    background_color: str = "transparent"  # Default background color

    def apply(self, file_path: str):
        """
        Apply the text overlay effect to the video file.
        :param file_path: Path to the input video file
        """
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            # Use ffmpeg to add text overlay
            (
                ffmpeg.input(file_path)
                .filter(
                    "drawtext",
                    text=self.text,
                    x=self.position[0],
                    y=self.position[1],
                    fontsize=self.font_size,
                    fontcolor=self.color,
                    box=1,
                    boxcolor=self.background_color,
                )
                .output(temp_file.name, vcodec="libx264", acodec="copy")
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
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            (
                ffmpeg.input(file_path, ss=self.start_time, to=self.end_time)
                .output(temp_file.name, vcodec="libx264", acodec="copy")
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
