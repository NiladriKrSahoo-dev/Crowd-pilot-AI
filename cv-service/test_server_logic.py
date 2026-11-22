import unittest
from fastapi import HTTPException
import server


class TestServerLogic(unittest.TestCase):
    def test_next_level_thresholds(self):
        # Green baseline
        self.assertEqual(server.next_level("GREEN", 0.0), "GREEN")
        self.assertEqual(server.next_level("GREEN", 1.5), "GREEN")
        # Amber trigger
        self.assertEqual(server.next_level("GREEN", 2.0), "AMBER")
        self.assertEqual(server.next_level("GREEN", 3.0), "AMBER")
        # Red trigger
        self.assertEqual(server.next_level("AMBER", 4.0), "RED")
        # Check trigger (density > MAX_PLAUSIBLE = 8.0)
        self.assertEqual(server.next_level("RED", 8.5), "CHECK")
        self.assertEqual(server.next_level("GREEN", 9.0), "CHECK")

    def test_next_level_hysteresis(self):
        # Red drops below 3.6 to become Amber
        self.assertEqual(server.next_level("RED", 3.8), "RED")
        self.assertEqual(server.next_level("RED", 3.5), "AMBER")
        self.assertEqual(server.next_level("RED", 1.5), "GREEN")

        # Amber drops below 1.8 to become Green
        self.assertEqual(server.next_level("AMBER", 1.9), "AMBER")
        self.assertEqual(server.next_level("AMBER", 1.7), "GREEN")

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

    def test_recommend_and_routes(self):
        with server.lock:
            server.publish_sites()

        # Test valid recommendation
        res = server.api_recommend(gate="North gate", want="A")
        self.assertIn("send", res)
        self.assertIn("send_name", res)
        self.assertIn("message", res)
        self.assertIn("redirected", res)

        # Test invalid gate
        with self.assertRaises(HTTPException):
            server.api_recommend(gate="Nonexistent gate", want="A")

        # Test invalid want
        with self.assertRaises(HTTPException):
            server.api_recommend(gate="North gate", want="Z")

        # Test public_sites
        sites = server.public_sites()
        self.assertIn("gates", sites)
        self.assertIn("sites", sites)
        self.assertTrue(len(sites["gates"]) > 0)
        for s in sites["sites"]:
            self.assertIn("id", s)
            self.assertIn("name", s)
            self.assertIn("status", s)
            # Public sites should NOT leak people counts
            self.assertNotIn("people", s)
            self.assertNotIn("capacity", s)

        # Test get_state
        state = server.get_state()
        self.assertIn("ready", state)
        self.assertIn("calibrated", state)
        self.assertIn("sites", state)
        self.assertIn("zones", state)
        self.assertIn("alerts", state)
        self.assertIn("history", state)

    def test_admin_closed(self):
        with server.lock:
            server.SITES["B"]["closed"] = False
            server.publish_sites()

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

        # Check public sites reflect CLOSED
        pub = server.public_sites()
        site_b = next(s for s in pub["sites"] if s["id"] == "B")
        self.assertEqual(site_b["status"], "CLOSED")

        # Reopen
        req_reopen = server.AdminClosedRequest(site="B", closed=False, pin="1234")
        res_reopen = server.admin_closed(req_reopen)
        self.assertEqual(res_reopen, {"site": "B", "closed": False})
        self.assertFalse(server.SITES["B"]["closed"])


if __name__ == "__main__":
    unittest.main()
