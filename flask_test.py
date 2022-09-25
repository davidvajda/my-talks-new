import unittest
from server import app, sio, que, rooms


test_client = app.test_client()


class TestFlaskFunctions(unittest.TestCase):
    def test_index(self):
        res = test_client.get("/")
        self.assertTrue(res.status_code == 200)

    def test_signin(self):
        res_get = test_client.get("/signin")
        self.assertTrue(res_get.status_code == 200)

        res_post = test_client.post(
            "signin", data={"email": "test@test.com", "password": "Test1+"}
        )
        self.assertTrue(res_post.status_code == 200)
        session_res = test_client.get("/session")
        print(list(session_res))


if __name__ == "__main__":
    unittest.main()
