"""
Tests for the Digital Video assignment.

These tests verify that:

  - video.html exists and is linked from the personal site's home page
  - video.html contains an HTML5 <video> element with at least one
    <source> in mp4 format AND one in either ogv or webm format
  - the video is in landscape orientation (width >= height)
  - the video's duration is between 3 and 5 minutes (180-300 s)

Requires Selenium 4.6+ and Google Chrome.

NOTE: video duration checks need the browser to load enough of the video
to read its metadata. The test waits up to 30 seconds for that.
"""

import json
import pytest
from urllib.parse import urljoin
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


PAGE = "video.html"
MIN_DURATION_S = 180   # 3 minutes
MAX_DURATION_S = 300   # 5 minutes
METADATA_TIMEOUT_S = 30


def _build_url(site_url, page=""):
  base = site_url.rstrip("/")
  if not page:
    return base + "/"
  return base + "/" + page.lstrip("/")


class Tests:

  @pytest.fixture(scope="class")
  def settings(self):
    with open('./settings.json', 'r') as f:
      yield json.load(f)

  @pytest.fixture(scope="class")
  def page_url(self, settings):
    return _build_url(settings["site_url"], PAGE)

  @pytest.fixture(scope="class")
  def driver(self, page_url):
    options = Options()
    options.add_argument("--window-size=1400,1000")
    options.add_argument("--autoplay-policy=no-user-gesture-required")
    driver = webdriver.Chrome(options=options)
    driver.get(page_url)
    yield driver
    driver.quit()

  def test_page_loads(self, driver):
    """video.html must load successfully."""
    assert driver.find_element(By.TAG_NAME, "body")

  def test_video_element_present(self, driver):
    """A <video> element must exist on video.html."""
    videos = driver.find_elements(By.TAG_NAME, "video")
    assert videos, "No <video> element on video.html."

  def test_video_has_mp4_source(self, driver):
    """A <source> of type mp4 must be inside the <video>."""
    sources = driver.find_elements(By.CSS_SELECTOR, "video source")
    types = [(s.get_attribute("type") or "").lower() for s in sources]
    srcs = [(s.get_attribute("src") or "").lower() for s in sources]
    has_mp4 = any("mp4" in t for t in types) or any(s.endswith(".mp4") for s in srcs)
    assert has_mp4, (
      "The <video> element has no MP4 <source>. Required <source> "
      "types: at least one MP4 and one OGV (or WebM)."
    )

  def test_video_has_alternate_source(self, driver):
    """The <video> must also have an ogv (preferred) or webm source."""
    sources = driver.find_elements(By.CSS_SELECTOR, "video source")
    types = [(s.get_attribute("type") or "").lower() for s in sources]
    srcs = [(s.get_attribute("src") or "").lower() for s in sources]
    has_alt = any(t for t in types if "ogg" in t or "webm" in t) or any(
      s.endswith((".ogv", ".ogg", ".webm")) for s in srcs
    )
    assert has_alt, (
      "The <video> element has no fallback <source>. The README "
      "requires both MP4 and OGV (or WebM) for cross-browser playback."
    )

  def test_video_metadata_loads(self, driver):
    """
    The first <video> on the page must be able to load its metadata so
    we can inspect dimensions and duration.
    """
    ok = driver.execute_async_script(
      """
      var done = arguments[0];
      var timeout = arguments[1];
      var v = document.querySelector('video');
      if (!v) return done(false);
      if (v.readyState >= 1) return done(true);
      var timer = setTimeout(function () { done(false); }, timeout);
      v.addEventListener('loadedmetadata', function () {
        clearTimeout(timer); done(true);
      });
      try { v.load(); } catch (e) {}
      """,
      METADATA_TIMEOUT_S * 1000,
    )
    assert ok, (
      "The <video> element's metadata did not load within {}s. The "
      "video file may be missing, too large, or unreachable."
      .format(METADATA_TIMEOUT_S)
    )

  def test_video_is_landscape(self, driver):
    """The video must be in landscape orientation (width >= height)."""
    dims = driver.execute_script(
      "var v = document.querySelector('video'); return [v.videoWidth, v.videoHeight];"
    )
    w, h = dims[0], dims[1]
    assert w and h, "videoWidth / videoHeight unavailable."
    assert w >= h, (
      "Video is in portrait orientation ({}x{}). The README requires "
      "landscape.".format(w, h)
    )

  def test_video_duration_in_range(self, driver):
    """Video duration must be between 3 and 5 minutes (180-300s)."""
    duration = driver.execute_script(
      "return document.querySelector('video').duration;"
    )
    assert duration and duration > 0, "videoDuration was 0 or unavailable."
    assert MIN_DURATION_S <= duration <= MAX_DURATION_S, (
      "Video duration is {:.1f}s; the README requires 3-5 minutes "
      "({}-{}s).".format(duration, MIN_DURATION_S, MAX_DURATION_S)
    )

  def test_linked_from_home(self, settings):
    """The home page (index.html) must link to video.html."""
    home = _build_url(settings["site_url"])
    options = Options()
    options.add_argument("--window-size=1400,1000")
    driver = webdriver.Chrome(options=options)
    try:
      driver.get(home)
      try:
        elem = driver.find_element(
          By.CSS_SELECTOR,
          "a[href='{0}'], a[href$='/{0}']".format(PAGE),
        )
      except NoSuchElementException:
        elem = None
      assert elem, "The home page has no link to video.html."
    finally:
      driver.quit()

  def test_source_video_url_set(self, settings):
    """settings.json must declare a source_video_url that is a real URL."""
    url = settings.get("source_video_url", "")
    assert url.startswith("http://") or url.startswith("https://"), (
      "settings.json 'source_video_url' is not a real URL: {!r}".format(url)
    )
