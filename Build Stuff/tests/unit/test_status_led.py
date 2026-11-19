import unittest
from unittest.mock import patch
import config
from banshee import status_led as led


class Pixel:
    def __init__(self):
        self.color=None
        self.writes=0
        self.fail=False
    def __setitem__(self,index,color):
        if self.fail:
            raise OSError('pixel failure')
        self.color=color
    def write(self):
        self.writes+=1


class Timer:
    PERIODIC=1
    def init(self,**kwargs):
        self.callback=kwargs['callback']
    def deinit(self):
        self.closed=True


class Button:
    def __init__(self, value=1):
        self.level = value
    def value(self):
        return self.level


class LEDTests(unittest.TestCase):
    def setUp(self):
        self.now=0
        self.pixel,self.timer=Pixel(),Timer()
        self.led=led.StatusLED(self.pixel,lambda:self.timer,lambda:self.now,brightness=1)
    def tick(self,now):
        self.now=now
        self.timer.callback(self.timer)
        return self.pixel.color

    def test_unique_color_count_groups_and_dark_pause(self):
        signatures = set()
        for state, (color, segments) in led.PATTERNS.items():
            if state == 'off':
                continue
            self.assertNotIn((color, segments), signatures)
            signatures.add((color, segments))
            self.now = 0
            self.led.set(state)
            self.assertEqual(self.tick(0), color)
            self.assertEqual(self.tick(180), (0,0,0))
            self.assertEqual(segments[-1], 1200)
            self.assertIn(len(segments), (2,4,6))
            self.assertEqual(self.tick(sum(segments)-1), (0,0,0))
            self.assertEqual(self.tick(sum(segments)), color)

    def test_polling_same_state_keeps_burst_phase(self):
        self.led.set('link_lost')
        self.tick(400)
        started = self.led.started
        self.led.set('link_lost')
        self.assertEqual(self.led.started, started)
        self.assertEqual(self.pixel.color, (255,0,0))

    def test_activity_cannot_hide_persistent_fault(self):
        self.led.set('error')
        self.led.pulse('capture')
        self.assertIsNone(self.led.overlay)
        self.assertEqual(self.tick(0),(255,0,0))

    def test_brightness_and_write_suppression(self):
        self.led.brightness=.1
        self.led.set('wifi_up')
        self.assertEqual(self.pixel.color,(0,25,25))
        count=self.pixel.writes
        self.tick(50)
        self.assertEqual(self.pixel.writes,count)

    def test_hardware_error_cannot_escape_timer_callback(self):
        self.led.set('wifi_up')
        self.pixel.fail=True
        self.tick(180)
        self.assertIn('pixel failure',self.led.error)
        self.led.close()
        self.assertTrue(self.timer.closed)

    def test_heartbeat_timeout_and_recovery(self):
        with patch.object(led,'set') as show:
            led.telemetry(None,0)
            show.assert_called_with('waiting')
            led.telemetry(100,200)
            show.assert_called_with('connected')
            led.telemetry(100,100+config.HEARTBEAT_TIMEOUT*1000+1)
            show.assert_called_with('link_lost')

    def test_disabled_indicator_has_no_hardware_side_effects(self):
        with patch.object(config,'RGB_ENABLED',False),patch.object(led,'_controller',None):
            self.assertIsNone(led.controller())
            led.set('error')

    def test_mute_preserves_current_state_and_phase(self):
        self.led.set('streaming')
        self.led.set_enabled(False)
        self.assertEqual(self.pixel.color,(0,0,0))
        self.tick(350)
        self.led.set('streaming')
        self.assertEqual(self.pixel.color,(0,0,0))
        self.led.set_enabled(True)
        self.assertEqual(self.pixel.color,(0,0,0))
        self.led.set_enabled(False)
        self.led.set('link_lost')
        self.assertEqual(self.led.state,'link_lost')
        self.assertEqual(self.pixel.color,(0,0,0))
        self.led.set_enabled(True)
        self.assertEqual(self.pixel.color,(255,0,0))

    def test_boot_button_debounces_and_toggles_once_per_press(self):
        button=Button()
        self.led.button=button
        self.tick(0)
        self.tick(50)  # Stable released button arms the next press.
        button.level=0
        self.tick(100)
        button.level=1
        self.tick(120)
        button.level=0
        self.tick(140)
        self.assertTrue(self.led.enabled)
        self.tick(190)
        self.assertFalse(self.led.enabled)
        self.tick(1000)  # Holding the button never repeats.
        self.assertFalse(self.led.enabled)
        button.level=1
        self.tick(1050)
        self.tick(1100)
        button.level=0
        self.tick(1150)
        self.tick(1200)
        self.assertTrue(self.led.enabled)

    def test_boot_held_at_start_requires_release_before_toggle(self):
        button=Button(0)
        self.led.button=button
        self.tick(0)
        self.tick(500)
        self.assertTrue(self.led.enabled)
        button.level=1
        self.tick(600)
        self.tick(650)
        button.level=0
        self.tick(700)
        self.tick(750)
        self.assertFalse(self.led.enabled)

    def test_button_failure_is_contained_and_close_keeps_pixel_dark(self):
        class BrokenButton:
            def value(self):
                raise OSError('button fault')
        self.led.button=BrokenButton()
        self.led.set('streaming')
        self.assertIsNone(self.led.button)
        self.assertIn('button fault',self.led.button_error)
        self.assertIsNone(self.led.error)
        self.assertEqual(self.pixel.color,(0,50,255))
        self.led.close()
        self.tick(350)
        self.led.set('error')
        self.assertEqual(self.pixel.color,(0,0,0))

    def test_button_config_rejects_output_or_reserved_alternative_pins(self):
        with patch.object(config,'RGB_BUTTON_PIN',48):
            with self.assertRaisesRegex(ValueError,'input GPIO0'):
                config.validate_board()
