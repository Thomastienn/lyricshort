import os
import tempfile
from typing import Sequence
import math

import ffmpeg
import srt

from logger import MyLogger
from utils import StreamUtils, FontUtils
from structures import (
    Effect,
    TrimEffect,
    TextOverlayEffect,
    TextOverlayProperties,
    FillOverlayEffect,
    TextPosition,
    UserPrompts,
)


class EditorEffects:
    def __init__(
        self,
        file_path: str,
        subtitle_path: str,
        start_time: float = 25,
        duration: float = 20,
        metadata=None,
    ):
        self.file_path = file_path
        self.subtitle_path = subtitle_path
        self.logger = MyLogger.get_logger("EditorEffects")
        self.metadata = metadata
        self.start_time = start_time
        self.duration = duration

    def apply_effects_individual(self, effects: Sequence[Effect]):
        """
        Apply a single effect to the video.
        :param effect: Effect instance
        """
        for effect in effects:
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

    def apply_effects(self, effects: Sequence[Effect]):
        """
        Apply a list of effects to the video.
        :param effects: List of Effect instances
        """
        # self.apply_effects_individual(effects)
        # return
        if not effects:
            return

        cnt = sum(isinstance(effect, TrimEffect) for effect in effects)
        if cnt > 1:
            self.logger.error("Use only one TrimEffect at a time. Found multiple.")
            raise ValueError("Multiple TrimEffects found, only one is allowed.")

        if cnt == 1:
            assert isinstance(effects[0], TrimEffect), "First effect must be TrimEffect"

        self.logger.info(
            f"Applying effects: {[effect.__class__.__name__ for effect in effects]}"
        )
        effects[0].apply(self.file_path)
        input_stream = ffmpeg.input(self.file_path)
        video_node: ffmpeg.nodes.FilterableStream = input_stream.video
        audio_node = input_stream.audio

        for effect in effects:
            video_node: ffmpeg.nodes.FilterableStream = effect.video_node(
                video_node, self.file_path
            )

        try:
            audio_codec = StreamUtils.get_audio_codec(self.file_path)
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
                    .global_args(*Effect.GLOBAL_ARGS)
                    .run()
                )
                os.replace(temp_file.name, self.file_path)

        except ffmpeg.Error as e:
            self.logger.error(f"Error applying effects : {e}")
            self.logger.error(
                e.stdout.decode("utf-8") if e.stdout else "No ffmpeg stdout"
            )
            self.logger.error(
                e.stderr.decode("utf-8") if e.stderr else "No ffmpeg stderr"
            )
            raise

        self.logger.info("All effects applied successfully.")

    def effects_vid(
        self,
        user_prompts: UserPrompts,
    ):
        trim = TrimEffect(
            start_time=self.start_time, end_time=self.start_time + self.duration
        )
        fill_overlay = FillOverlayEffect(color="black", opacity=0.6)
        # text_overlay = TextOverlayEffect(
        #     texts=[
        #         TextOverlayProperties(
        #             text=f"{user_prompts.title} by {user_prompts.author}",
        #             position=TextPosition(
        #                 vertical="top",
        #                 horizontal="center",
        #             ),
        #             font_size=50,
        #             color="white",
        #             duration=math.ceil(self.duration),
        #             offset=(0, 20),  # Offset for top margin
        #         )
        #     ]
        # )

        try:
            self.apply_effects([trim, fill_overlay])
            self.logger.info(f"Applied all effects to {self.file_path}")
        except ffmpeg.Error as e:
            self.logger.error(f"Error applying effects: {e}")
            raise

    def add_subtitles(self):
        """
        Add subtitles to the video.
        """
        FONT_SIZE = 35
        INIT_OFFSET = 20
        LINE_GAP = 5

        if not os.path.exists(self.subtitle_path):
            self.logger.error(f"Subtitle file {self.subtitle_path} does not exist.")
            return

        with open(self.subtitle_path, "r", encoding="utf-8") as file:
            subtitles = srt.parse(file.read())

        subtitle_props: list[TextOverlayProperties] = []
        overlay_spots: dict[int, float] = {}
        _, font_height = FontUtils.get_font_dimensions(FONT_SIZE, "PLACEHOLDER")

        for subtitle in subtitles:
            text: str = subtitle.content.replace("\n", " ").strip()
            start_time: float = subtitle.start.total_seconds() - self.start_time
            end_time: float = subtitle.end.total_seconds() - self.start_time

            if end_time < 0:
                self.logger.info(
                    f"Subtitle {subtitle.index} '{text}' is outside the trim range, skipping."
                )
                continue
            if start_time > self.duration:
                self.logger.info(
                    f"Subtitle {subtitle.index} '{text}' is outside the duration range, ending."
                )
                break

            current_offset = INIT_OFFSET
            while True:
                if current_offset in overlay_spots:
                    end_last = overlay_spots[current_offset]
                    if start_time >= end_last:
                        break
                else:
                    break
                current_offset += FONT_SIZE

            overlay_spots[current_offset] = end_time
            self.logger.info(
                f"Adding subtitle: {subtitle.index}, '{text}' from {start_time} to {end_time}"
            )

            subtitle_prop = TextOverlayProperties(
                text=text,
                position=TextPosition(
                    vertical="center",
                    horizontal="center",
                ),
                font_size=FONT_SIZE,
                color="white",
                start_time=start_time,
                duration=int(end_time - start_time),
                offset=(
                    0,
                    current_offset
                    + (current_offset - INIT_OFFSET) // FONT_SIZE * LINE_GAP,
                ),
            )
            subtitle_props.append(subtitle_prop)

        TextOverlayEffect(texts=subtitle_props).apply(self.file_path)
