from logging import getLogger, StreamHandler, Formatter, getLevelName, DEBUG, INFO

import config

logger = getLogger(__name__)

# ログのフォーマットを定義
# JSON形式で出力する
formatter = Formatter(
    '{"time": "%(asctime)s", "name": "%(name)s", "level": "%(levelname)s", "message": "%(message)s"}'
)

# ログの出力先を標準出力に設定
handler = StreamHandler()

# ログのフォーマットを設定
handler.setFormatter(formatter)

# ログのレベルを設定
handler.setLevel(DEBUG)

# ロガーにハンドラを設定
logger.addHandler(handler)

# ログのレベルを設定
logger.setLevel(getLevelName(config.LOG_LEVEL))

def main():
    logger.debug("This is debug log")
    logger.info("This is info log")
    logger.warning("This is warning log")
    logger.error("This is error log")
    logger.critical("This is critical log")

if __name__ == "__main__":
    main()
