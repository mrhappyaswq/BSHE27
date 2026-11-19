from time import ticks_ms
import jpeg
import gc

NR = 100
IMG_PATH = "000.jpeg"

with open(IMG_PATH, "rb") as f:
    IMG = f.read()

def fps(n, dt_ms):
    return n * 1000 / dt_ms if dt_ms > 0 else 0.0

def bpp(fmt):
    # 依你的 README 格式清單做常用 bpp 推斷
    if fmt in ("RGB565_BE", "RGB565_LE", "CbYCrY", "YCbYCr"):
        return 2
    if fmt in ("RGB888",):
        return 3
    if fmt in ("RGBA",):
        return 4
    # fallback
    return 2

def decoder_bench():
    gc.collect()
    print("Decoder Benchmark (NEW API)")
    print("Input Image Size:", len(IMG), "bytes")

    for fmt in ("RGB565_BE", "RGB565_LE", "RGB888", "CbYCrY"):
        print("\nFormat:", fmt)
        _bpp = bpp(fmt)

        # ---- 1) normal decode (block=False) ----
        dec = jpeg.Decoder(pixel_format=fmt, rotation=0, block=False)
        t0 = ticks_ms()
        for _ in range(NR):
            _ = dec.decode(IMG)
        dt = ticks_ms() - t0
        print("FPS normal decode (decode, block=False):", "%.2f" % fps(NR, dt))

        # ---- 2) block decode (decode, block=True) ----
        dec = jpeg.Decoder(pixel_format=fmt, rotation=0, block=True)
        info = dec.get_img_info(IMG)
        w, h, blocks = info[0], info[1], info[2]

        t0 = ticks_ms()
        for _ in range(NR):
            for _i in range(blocks):
                _ = dec.decode(IMG)
        dt = ticks_ms() - t0
        print("FPS block decode (decode, block=True, blocks=%d):" % blocks, "%.2f" % fps(NR, dt))

        # ---- prepare framebuffer ----
        fb = bytearray(w * h * _bpp)

        # ---- 3) block decode + Python write (slice copy) ----
        # 先取一塊推算 block size（只用於 slice 拼接測試）
        dec_tmp = jpeg.Decoder(pixel_format=fmt, rotation=0, block=True, return_bytes=True)
        _ = dec_tmp.get_img_info(IMG)
        blk0 = dec_tmp.decode(IMG)
        blk_size = len(blk0)

        # 正式測試：每塊 decode() 回 bytes，再 slice 拷貝到 fb
        dec3 = jpeg.Decoder(pixel_format=fmt, rotation=0, block=True, return_bytes=True)
        _ = dec3.get_img_info(IMG)

        t0 = ticks_ms()
        for _ in range(NR):
            for i in range(blocks):
                blk = dec3.decode(IMG)
                off = i * blk_size
                fb[off:off + blk_size] = blk
        dt = ticks_ms() - t0
        print("FPS block decode + write (python slice):", "%.2f" % fps(NR, dt))

        # ---- 4) NEW: decode_into step (blocks=1) ----
        # 每輪做 blocks 次，每次做 1 block，done 只有最後一次會 True
        dec4 = jpeg.Decoder(pixel_format=fmt, rotation=0, block=True)
        _ = dec4.get_img_info(IMG)

        t0 = ticks_ms()
        for _ in range(NR):
            for _i in range(blocks):
                done = dec4.decode_into(IMG, fb, blocks=1)
        dt = ticks_ms() - t0
        print("FPS decode_into step (blocks=1):", "%.2f" % fps(NR, dt))

        # ---- 5) NEW: decode_into full (default blocks=0) ----
        # 每輪只呼叫一次，應該直接完成一輪 (done=True)
        dec5 = jpeg.Decoder(pixel_format=fmt, rotation=0, block=True)
        _ = dec5.get_img_info(IMG)

        t0 = ticks_ms()
        for _ in range(NR):
            done = dec5.decode_into(IMG, fb)  # default blocks=0 (full)
            # 理論上 done 應為 True
        dt = ticks_ms() - t0
        print("FPS decode_into full (default blocks=0):", "%.2f" % fps(NR, dt))


def encoder_bench():
    print("\nEncoder Benchmark")
    # 先解成 RGB888 當作 encoder input
    dec = jpeg.Decoder(pixel_format="RGB888", rotation=0, block=False)
    info = dec.get_img_info(IMG)
    w, h = info[0], info[1]
    img_dec = bytes(dec.decode(IMG))
    del dec
    gc.collect()

    for q in (100, 90, 80, 70, 60):
        enc = jpeg.Encoder(pixel_format="RGB888", quality=q, height=h, width=w)
        t0 = ticks_ms()
        for _ in range(NR):
            _ = enc.encode(img_dec)
        dt = ticks_ms() - t0
        print("FPS encode quality %d:" % q, "%.2f" % fps(NR, dt))
        gc.collect()


decoder_bench()
encoder_bench()
