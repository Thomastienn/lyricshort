import os
import logging
from typing import Sequence

import ffmpeg
import srt

from structures import (
    Effect,
    TrimEffect,
    TextOverlayEffect,
    TextOverlayProperties,
    FillOverlayEffect,
    TextPosition,
    UserPrompts,
)
from utils import StreamUtils


class EditorEffects:
    def __init__(
        self, file_path: str, subtitle_path: str, logger: logging.Logger, metadata=None
    ):
        self.file_path = file_path
        self.subtitle_path = subtitle_path
        self.logger = logger
        self.metadata = metadata
        self.start_time = 25
        self.duration = 20

    def apply_effects(self, effects: Sequence[Effect]):
        """
        Apply a list of effects to the video.
        :param effects: List of Effect instances
        """
        for effect in effects:
            self.logger.info(f"Applying effect: {effect.__class__.__name__}")
            try:
                effect.apply(self.file_path)
            except ffmpeg.Error as e:
                self.logger.error(
                    f"Error applying effect {effect.__class__.__name__}: {e}"
                )
                self.logger.error(
                    e.stdout.decode("utf-8") if e.stdout else "No ffmpeg stdout"
                )
                self.logger.error(
                    e.stderr.decode("utf-8") if e.stderr else "No ffmpeg stderr"
                )
                raise
            self.logger.info(
                f"Effect {effect.__class__.__name__} applied successfully."
            )

    def effects_vid(
        self,
        user_prompts: UserPrompts,
    ):
        trim = TrimEffect(
            start_time=self.start_time, end_time=self.start_time + self.duration
        )
        fill_overlay = FillOverlayEffect(color="black", opacity=0.4)
        text_overlay = TextOverlayEffect(
            texts=[
                TextOverlayProperties(
                    text=f"{user_prompts.title} by {user_prompts.author}",
                    position=TextPosition(
                        vertical="top",
                        horizontal="center",
                    ),
                    font_size=50,
                    color="white",
                    duration=self.duration,
                )
            ]
        )

        try:
            self.apply_effects([trim, fill_overlay, text_overlay])
            self.logger.info(f"Applied all effects to {self.file_path}")
        except ffmpeg.Error as e:
            self.logger.error(f"Error applying effects: {e}")
            raise

    def add_subtitles(self):
        """
        Add subtitles to the video.
        """
        if not os.path.exists(self.subtitle_path):
            self.logger.error(f"Subtitle file {self.subtitle_path} does not exist.")
            return

        with open(self.subtitle_path, "r", encoding="utf-8") as file:
            subtitles = srt.parse(file.read())

        subtitle_props: list[TextOverlayProperties] = []
        for subtitle in subtitles:
            text: str = subtitle.content
            start_time: float = subtitle.start.total_seconds() - self.start_time
            end_time: float = subtitle.end.total_seconds() - self.start_time

            self.logger.info(
                f"Adding subtitle: {subtitle.index}, '{text}' from {start_time} to {end_time}"
            )

            subtitle_prop = TextOverlayProperties(
                text=text,
                position=TextPosition(
                    vertical="bottom",
                    horizontal="center",
                ),
                font_size=24,
                color="white",
                start_time=start_time,
                duration=int(end_time - start_time),
            )
            subtitle_props.append(subtitle_prop)

        subtitle_effect = TextOverlayEffect(texts=subtitle_props)
        self.apply_effects([subtitle_effect])
