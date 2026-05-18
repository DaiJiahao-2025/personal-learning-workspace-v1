import unittest

from backend.app.video_links import extract_bilibili_bvid, extract_bilibili_page


class VideoLinkTests(unittest.TestCase):
    def test_extracts_bilibili_bvid_and_page(self) -> None:
        url = "https://www.bilibili.com/video/BV1Y84y1L7Nn/?p=200"
        self.assertEqual(extract_bilibili_bvid(url), "BV1Y84y1L7Nn")
        self.assertEqual(extract_bilibili_page(url), 200)

    def test_invalid_bilibili_page_defaults_to_one(self) -> None:
        self.assertEqual(extract_bilibili_page("https://www.bilibili.com/video/BV1xx?p=oops"), 1)


if __name__ == "__main__":
    unittest.main()
