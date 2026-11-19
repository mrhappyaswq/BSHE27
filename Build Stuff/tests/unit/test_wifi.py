import asyncio
import importlib
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch


class AccessPointTests(unittest.TestCase):
    def setUp(self):
        with patch.dict(sys.modules, {'network': SimpleNamespace()}):
            self.app=importlib.import_module('apps.camera_web')
        self.enabled=False
        self.ap=Mock()
        def active(value=None):
            if value is not None:
                self.enabled=value
            return self.enabled
        self.ap.active.side_effect=active
        self.ap.ifconfig.return_value=('192.168.4.1','','','')
        self.wlan=Mock(return_value=self.ap)
        self.wlan.IF_AP=1
        patcher=patch.object(self.app,'network',SimpleNamespace(WLAN=self.wlan,AP_IF=1))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_hotspot_is_visible_and_password_protected(self):
        self.assertIs(self.app.start_access_point(),self.ap)
        self.assertTrue(self.enabled)
        options=self.ap.config.call_args.kwargs
        self.assertFalse(options['hidden'])
        self.assertEqual(options['ssid'],'BSHE27-Camera')
        self.assertEqual(options['security'],3)
        self.assertEqual(options['channel'],1)
        self.assertGreaterEqual(len(options['key']),8)
        self.ap.ifconfig.assert_any_call(('192.168.4.1','255.255.255.0','192.168.4.1','192.168.4.1'))

    def test_older_camera_firmware_gets_legacy_wifi_keywords(self):
        self.ap.config.side_effect=[ValueError('unknown parameter'),None]
        self.app.start_access_point()
        self.assertEqual(self.ap.config.call_args.kwargs['authmode'],3)
        self.assertEqual(self.ap.config.call_args.kwargs['essid'],'BSHE27-Camera')

    def test_wifi_error_turns_ap_off_and_is_not_hidden(self):
        self.ap.config.side_effect=OSError('radio failed')
        with self.assertRaisesRegex(OSError,'radio failed'):
            self.app.start_access_point()
        self.assertFalse(self.enabled)

    def test_missing_camera_keeps_ap_alive_for_error_page(self):
        observed=[]
        async def serve(camera,error=None,ap=None,telemetry=None,camera_factory=None):
            self.assertIsNotNone(camera_factory)
            try:
                camera = camera_factory()
            except Exception as exc:
                error = str(exc)
            observed.append((self.enabled,camera,error))
        with patch.object(self.app,'open_camera',side_effect=RuntimeError('camera module missing')), patch.object(self.app,'serve',serve):
            self.app.main()
        self.assertEqual(observed,[(True,None,'camera module missing')])
        self.assertFalse(self.enabled)


    def test_device_connect_and_disconnect_change_indicator(self):
        self.enabled=True
        with patch.object(self.app.status_led,'set') as show:
            self.ap.isconnected.return_value=False
            self.app.update_wifi_led(self.ap)
            show.assert_called_with('wifi_up')
            self.ap.isconnected.return_value=True
            self.app.update_wifi_led(self.ap)
            show.assert_called_with('wifi_connected')
            self.app.update_wifi_led(self.ap,'camera driver missing')
            show.assert_called_with('wifi_connected_camera_error')
            self.ap.isconnected.return_value=False
            self.app.update_wifi_led(self.ap,'camera driver missing')
            show.assert_called_with('wifi_up_camera_error')

    def test_station_query_failure_does_not_invent_a_connection(self):
        self.enabled=True
        self.ap.isconnected.side_effect=OSError('not supported')
        details=self.app.wifi_details(self.ap)
        self.assertTrue(details['wifi_up'])
        self.assertIsNone(details['device_connected'])
