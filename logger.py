import sys
import logging


class MyLogger:
    def __init__(self, name):
        self.name = name

    def get_logger(self) -> logging.Logger:
        logger = logging.getLogger()
        logger.setLevel(logging.INFO)

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )
        file_handler = logging.FileHandler("output.log", mode="w")
        file_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
            )
        )

        logger.addHandler(console_handler)
        logger.addHandler(file_handler)

        return logger
