import unittest
from fastapi import HTTPException
import server


class TestServerLogic(unittest.TestCase):
    def setUp(self):
        # Reset server state between tests
        with server.lock:
            for sid, cfg in server.SITES.items():
                cfg["closed"] = False
                server.loads[sid] = 0.5 * cfg["capacity"]
                server.pending[sid] = 0.0
            server.alerts.clear()
            server.advisories.clear()
            server.no_room_events.clear()
            server.last_no_room_alert_time = 0.0
            server.publish_sites()

    def test_next_level_thresholds_and_hysteresis(self):
        # GREEN to AMBER at 2.0
        self.assertEqual(server.next_level("GREEN", 0.0), "GREEN")
        self.assertEqual(server.next_level("GREEN", 1.99), "GREEN")
        self.assertEqual(server.next_level("GREEN", 2.0), "AMBER")

        # AMBER stays at or above 1.8; drops to GREEN below 1.8
        self.assertEqual(server.next_level("AMBER", 1.8), "AMBER")
        self.assertEqual(server.next_level("AMBER", 1.79), "GREEN")

        # AMBER to RED at 4.0
        self.assertEqual(server.next_level("AMBER", 3.99), "AMBER")
        self.assertEqual(server.next_level("AMBER", 4.0), "RED")

        # RED stays at or above 3.6; drops to AMBER below 3.6
        self.assertEqual(server.next_level("RED", 3.6), "RED")
        self.assertEqual(server.next_level("RED", 3.59), "AMBER")
        self.assertEqual(server.next_level("RED", 1.7), "GREEN")

        # CHECK above 8
        self.assertEqual(server.next_level("RED", 8.0), "RED")
        self.assertEqual(server.next_level("RED", 8.01), "CHECK")
        self.assertEqual(server.next_level("GREEN", 8.5), "CHECK")

    def test_suggested_action(self):
        self.assertIn("limit new entry", server.suggested_action("RED", 1))
        self.assertIn("keep watching", server.suggested_action("AMBER", 2))
        self.assertIn("impossible", server.suggested_action("CHECK", 3))
        self.assertEqual(server.suggested_action("GREEN", 4), "")

    def test_status_for(self):
        self.assertEqual(server.status_for(0.5), "CLEAR")
        self.assertEqual(server.status_for(0.6), "BUSY")
        self.assertEqual(server.status_for(0.84), "BUSY")
        self.assertEqual(server.status_for(0.85), "VERY BUSY")

    def test_redirects_spread_across_pandals(self):
        # Make wanted pandal A very busy
        with server.lock:
            server.loads["A"] = 0.90 * server.SITES["A"]["capacity"]
            server.publish_sites()

        # Send multiple recommendation requests and collect chosen destinations
        destinations = []
        for _ in range(6):
            with server.lock:
                res = server.recommend("North gate", "A")
            self.assertTrue(res["redirected"])
            self.assertIsNotNone(res["send"])
            self.assertNotEqual(res["send"], "A")
            dest = res["send"]
            # Verify the destination was not already pushed past 85% BEFORE being chosen
            # (effective occupancy before the last increment was < 0.85)
            dest_occ_after = server.occupancy(dest)
            # The increment was 1 group (= 8 people / capacity)
            inc = server.REDIRECT_WEIGHT / server.SITES[dest]["capacity"]
            occ_before = dest_occ_after - inc
            self.assertLess(occ_before, server.VERY_BUSY_AT)
            destinations.append(dest)

        # Confirm redirects spread across more than one alternative pandal
        unique_destinations = set(destinations)
        self.assertGreater(len(unique_destinations), 1, "Redirects should be spread across alternatives")

    def test_closed_pandal_never_recommended(self):
        with server.lock:
            server.SITES["B"]["closed"] = True
            server.publish_sites()

        # Requesting open pandal A when A is very busy
        server.loads["A"] = 0.90 * server.SITES["A"]["capacity"]
        for gate in server.WALK_MIN:
            res = server.recommend(gate, "A")
            self.assertNotEqual(res["send"], "B", "Closed pandal B must never be recommended as alternative")

        # Requesting closed pandal B directly
        for gate in server.WALK_MIN:
            res = server.recommend(gate, "B")
            self.assertNotEqual(res["send"], "B", "Closed pandal B must never recommend itself")
            if res["send"] is not None:
                self.assertFalse(server.SITES[res["send"]]["closed"])

        # When all pandals are closed
        with server.lock:
            for cfg in server.SITES.values():
                cfg["closed"] = True
            server.publish_sites()

        res = server.recommend("North gate", "A")
        self.assertIsNone(res["send"], "When all pandals are closed, send must be None")

    def test_all_busy_alert_fires_once_per_window(self):
        # Make all pandals busy so no open pandal has room
        with server.lock:
            for sid, cfg in server.SITES.items():
                server.loads[sid] = 0.95 * cfg["capacity"]
            server.publish_sites()

        public_alerts = [a for a in server.alerts if a["level"] == "PUBLIC"]
        self.assertEqual(len(public_alerts), 0)

        # 4 requests with no room
        for _ in range(4):
            with server.lock:
                res = server.recommend("North gate", "A")
                self.assertIsNone(res["send"])
            public_alerts = [a for a in server.alerts if a["level"] == "PUBLIC"]
            self.assertEqual(len(public_alerts), 0)

        # 5th request triggers the alert
        with server.lock:
            res = server.recommend("North gate", "A")
            self.assertIsNone(res["send"])
            server.publish_sites()

        public_alerts = [a for a in server.alerts if a["level"] == "PUBLIC"]
        self.assertEqual(len(public_alerts), 1)
        alert = public_alerts[0]
        self.assertIsNone(alert["zone"])
        self.assertEqual(alert["level"], "PUBLIC")
        self.assertIn("could not be redirected: no open pandal has room", alert["message"])
        self.assertEqual(alert["action"], "Consider opening extra capacity or pausing entry at the gates")

        # Subsequent requests within 60s do NOT trigger another alert
        for _ in range(5):
            with server.lock:
                server.recommend("North gate", "A")
                server.publish_sites()

        public_alerts = [a for a in server.alerts if a["level"] == "PUBLIC"]
        self.assertEqual(len(public_alerts), 1, "Alert must fire at most once per 60 second window")

    def test_admin_closed_and_alerts(self):
        # Wrong PIN -> 403
        req_bad_pin = server.AdminClosedRequest(site="B", closed=True, pin="wrong")
        with self.assertRaises(HTTPException) as ctx:
            server.admin_closed(req_bad_pin)
        self.assertEqual(ctx.exception.status_code, 403)

        # Unknown site -> 400
        req_bad_site = server.AdminClosedRequest(site="UNKNOWN", closed=True, pin="1234")
        with self.assertRaises(HTTPException) as ctx:
            server.admin_closed(req_bad_site)
        self.assertEqual(ctx.exception.status_code, 400)

        # Successful close
        req_ok = server.AdminClosedRequest(site="B", closed=True, pin="1234")
        res = server.admin_closed(req_ok)
        self.assertEqual(res, {"site": "B", "closed": True})
        self.assertTrue(server.SITES["B"]["closed"])

        # Check ADMIN alert logged
        admin_alerts = [a for a in server.alerts if a["level"] == "ADMIN"]
        self.assertTrue(len(admin_alerts) >= 1)
        close_alert = admin_alerts[0]
        self.assertIsNone(close_alert["zone"])
        self.assertEqual(close_alert["level"], "ADMIN")
        self.assertIn("Pandal B closed by the authority", close_alert["message"])

        # Check public sites reflect CLOSED
        pub = server.public_sites()
        site_b = next(s for s in pub["sites"] if s["id"] == "B")
        self.assertEqual(site_b["status"], "CLOSED")

        # Check /api/state reflects closed: True
        st = server.get_state()
        site_b_state = next(s for s in st["sites"] if s["id"] == "B")
        self.assertTrue(site_b_state["closed"])
        self.assertEqual(site_b_state["status"], "CLOSED")

        # Reopen
        req_reopen = server.AdminClosedRequest(site="B", closed=False, pin="1234")
        res_reopen = server.admin_closed(req_reopen)
        self.assertEqual(res_reopen, {"site": "B", "closed": False})
        self.assertFalse(server.SITES["B"]["closed"])

        # Check reopen ADMIN alert logged
        admin_alerts = [a for a in server.alerts if a["level"] == "ADMIN"]
        reopen_alert = admin_alerts[0]
        self.assertIn("Pandal B reopened", reopen_alert["message"])

    def test_serve_build_or_fallback(self):
        resp_root = server.dashboard()
        resp_public = server.public_page()
        if server.os.path.isfile(server.INDEX_FILE):
            self.assertIsInstance(resp_root, server.FileResponse)
            self.assertEqual(resp_root.path, server.INDEX_FILE)
            self.assertIsInstance(resp_public, server.FileResponse)
            self.assertEqual(resp_public.path, server.INDEX_FILE)

        orig_index = server.INDEX_FILE
        try:
            server.INDEX_FILE = "/nonexistent/path/index.html"
            fallback_root = server.dashboard()
            fallback_public = server.public_page()
            self.assertIsInstance(fallback_root, server.HTMLResponse)
            self.assertIn("Crowd Pilot AI", fallback_root.body.decode("utf-8"))
            self.assertIsInstance(fallback_public, server.HTMLResponse)
            self.assertIn("Pandal crowd guide", fallback_public.body.decode("utf-8"))
        finally:
            server.INDEX_FILE = orig_index


if __name__ == "__main__":
    unittest.main()
