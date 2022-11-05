from json import load
import unittest
from server import app, sio, que, rooms
from os import environ
from dotenv import load_dotenv
import json

load_dotenv()

test_client = app.test_client()
class TestFlaskFunctions(unittest.TestCase):
    def test_index(self):
        res = test_client.get("/")
        self.assertTrue(res.status_code == 200)


    def test_signin(self):
        res_get = test_client.get("/signin")
        self.assertTrue(res_get.status_code == 200)

        # test_email = environ.get("TEST_EMAIL")
        # test_password = environ.get("TEST_PASSWORD")
        #
        # res_post = test_client.post(
        #     "signin", data={"email": test_email, "password": test_password}
        # )
        # session_res = test_client.get("/session")
        # self.assertTrue(res_post.status_code == 200)
        #
        # session = json.loads(session_res.data)
        # self.assertTrue(session.get("_flashes") != None)
        # self.assertTrue(session.get("user") != None)


if __name__ == "__main__":
    unittest.main()
