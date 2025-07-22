import sys
import logging


class MyLogger:
    AVAILABLE_LOGGERS: dict[str, logging.Logger] = {}

    @staticmethod
    def get_logger(name: str = "") -> logging.Logger:
        if name in MyLogger.AVAILABLE_LOGGERS:
            return MyLogger.AVAILABLE_LOGGERS[name]

        logger = logging.getLogger(name)
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

        MyLogger.AVAILABLE_LOGGERS[name] = logger
        return logger

    @staticmethod
    def log_apply(func):
        """
        Decorator to log the application of the effect.
        :param func: Function to be decorated
        """

        logger = MyLogger.get_logger("apply_effect")

        def wrapper(self, file_path: str, *args, **kwargs):
            if not file_path:
                raise ValueError("File path must be provided for using effect")
            try:
                logger.info(f"Applying effect: {self.__class__.__name__}")
                func(self, file_path, *args, **kwargs)
            except Exception as e:
                logger.error(f"Error applying effect {self.__class__.__name__}: {e}")
                raise
            logger.info(f"Effect {self.__class__.__name__} applied successfully")

        return wrapper
