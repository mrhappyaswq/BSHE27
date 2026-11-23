#pragma once

// Served directly from flash; the viewer needs no internet or external assets.
const char PAGE[] PROGMEM = R"HTML(<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>BSHE27 Camera</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; background: #111821; color: #edf4fc; font: 16px system-ui, sans-serif; }
    main { max-width: 960px; margin: auto; padding: 24px; }
    h1 { font-size: 26px; margin: 0; }
    p { color: #b4c4d7; line-height: 1.5; }
    .frame { background: #080c11; min-height: 240px; border-radius: 14px;
      overflow: hidden; display: grid; place-items: center; margin: 20px 0; }
    img { display: block; width: 100%; max-height: 70vh; object-fit: contain; }
    button, a { display: inline-block; background: #aad5ff; color: #102030; border: 0;
      border-radius: 8px; padding: 12px 18px; font: inherit; cursor: pointer;
      text-decoration: none; margin: 0 8px 8px 0; }
    button:disabled { opacity: .5; cursor: wait; }
    button:focus-visible, a:focus-visible { outline: 3px solid white; outline-offset: 3px; }
    #status { min-height: 24px; }
    small { color: #b4c4d7; }
  </style>
</head>
<body>
  <main>
    <h1>BSHE27 Camera</h1>
    <p>Live camera feed · 640 × 480 JPEG</p>
    <div class="frame"><img id="feed" alt="Camera feed stopped"></div>
    <button id="toggle" type="button" disabled>Start live view</button>
    <a href="/capture" target="_blank" rel="noopener">Open snapshot</a>
    <p id="status" role="status" aria-live="polite">Checking camera…</p>
    <small>One viewer at a time. Stay connected to the camera Wi-Fi.</small>
  </main>
  <script>
    const feed = document.getElementById('feed');
    const toggle = document.getElementById('toggle');
    const status = document.getElementById('status');
    let playing = false;

    function stop() {
      playing = false;
      feed.removeAttribute('src');
      feed.alt = 'Camera feed stopped';
      toggle.textContent = 'Start live view';
      status.textContent = 'Live view stopped.';
    }

    function start() {
      const url = new URL('/stream', location.href);
      url.port = '81';
      url.searchParams.set('t', Date.now());
      playing = true;
      feed.alt = 'Live camera feed';
      toggle.textContent = 'Stop live view';
      // Browsers may not fire an image load event until an MJPEG stream ends.
      status.textContent = 'Live view requested. If no picture appears, check power and Wi-Fi.';
      feed.src = url.href;
    }

    toggle.addEventListener('click', () => playing ? stop() : start());
    feed.addEventListener('error', () => {
      if (!playing) return;
      stop();
      status.textContent = 'Feed disconnected. Check power and Wi-Fi, then press Start live view.';
    });
    window.addEventListener('pagehide', stop);

    async function initialize() {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 5000);
      try {
        const response = await fetch('/status', { cache: 'no-store', signal: controller.signal });
        if (!response.ok) throw new Error('Status request failed');
        const camera = await response.json();
        if (!camera.ready) {
          status.textContent = 'Camera error: ' + camera.error;
          return;
        }
        toggle.disabled = false;
        start();
      } catch (error) {
        status.textContent = 'Camera unavailable. Reconnect to the camera Wi-Fi and reload.';
      } finally {
        clearTimeout(timeout);
      }
    }

    initialize();
  </script>
</body>
</html>)HTML";
