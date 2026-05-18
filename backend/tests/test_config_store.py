import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.app.config_store import (
    get_effective_bilibili_cookie,
    get_effective_proxy_url,
    load_ai_config,
    load_downloader_config,
    load_transcription_config,
    save_ai_config,
    save_downloader_config,
    save_transcription_config,
)
from backend.app.models import AiConfig, DownloaderConfig, TranscriptionConfig


class ConfigStoreTests(unittest.TestCase):
    def test_ai_config_round_trip_persists_saved_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "ai_config.json"
            data_dir = config_path.parent
            config = AiConfig(baseUrl="https://example.com/v1", apiKey="secret", modelName="demo")

            with patch("backend.app.config_store.AI_CONFIG_PATH", config_path), patch(
                "backend.app.config_store.DATA_DIR",
                data_dir,
            ):
                save_ai_config(config)
                loaded = load_ai_config()

            self.assertEqual(loaded, config)

    def test_downloader_config_prefers_saved_values_over_env(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "downloader_config.json"
            data_dir = config_path.parent

            with patch("backend.app.config_store.DOWNLOADER_CONFIG_PATH", config_path), patch(
                "backend.app.config_store.DATA_DIR",
                data_dir,
            ), patch.dict(
                "os.environ",
                {"HTTPS_PROXY": "http://env-proxy", "BILIBILI_COOKIE": "env-cookie"},
                clear=True,
            ):
                save_downloader_config(
                    DownloaderConfig(bilibiliCookie="saved-cookie", proxyUrl="http://saved-proxy")
                )

                self.assertEqual(load_downloader_config().proxy_url, "http://saved-proxy")
                self.assertEqual(get_effective_proxy_url(), "http://saved-proxy")
                self.assertEqual(get_effective_bilibili_cookie(), "saved-cookie")

    def test_transcription_config_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "transcription_config.json"
            data_dir = config_path.parent
            config = TranscriptionConfig(
                baseUrl="https://example.com/v1",
                apiKey="secret",
                modelName="transcribe-demo",
            )

            with patch("backend.app.config_store.TRANSCRIPTION_CONFIG_PATH", config_path), patch(
                "backend.app.config_store.DATA_DIR",
                data_dir,
            ):
                save_transcription_config(config)
                loaded = load_transcription_config()

            self.assertEqual(loaded, config)


if __name__ == "__main__":
    unittest.main()
