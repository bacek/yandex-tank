import json
from mimetools import Message
from urllib2 import HTTPError
import time

from Tank.API.client import TankAPIClient

from Tank.API.server import TankAPIHandler

from Tests.TankTests import TankTestCase


class TankAPIHandlerTestCase(TankTestCase):
    def setUp(self):
        self.obj = TankAPIHandler()

    def test_run_usual(self):
        res = json.loads(self.obj.handle_get(TankAPIClient.INITIATE_TEST_JSON)[2])
        self.assertNotEquals("", res["ticket"])
        res = json.loads(self.obj.handle_get(TankAPIClient.TEST_STATUS_JSON + "?ticket=" + res["ticket"])[2])
        self.assertEquals(TankAPIClient.STATUS_BOOKED, res["status"])
        fd = open("data/post.txt")

        message = Message(fd)
        message.parsetype()
        self.obj.handle_post(TankAPIClient.PREPARE_TEST_JSON + "?ticket=" + res["ticket"], message, fd)
        while True:
            res = json.loads(self.obj.handle_get(TankAPIClient.TEST_STATUS_JSON + "?ticket=" + res["ticket"])[2])
            if res['status'] == TankAPIClient.STATUS_PREPARED:
                break
            time.sleep(1)

        self.obj.handle_get(TankAPIClient.START_TEST_JSON + "?ticket=" + res["ticket"])
        for _ in range(1, 10):
            res = json.loads(self.obj.handle_get(TankAPIClient.TEST_STATUS_JSON + "?ticket=" + res["ticket"])[2])
            if res['status'] != TankAPIClient.STATUS_RUNNING:
                break
            time.sleep(1)

        self.obj.handle_get(TankAPIClient.INTERRUPT_TEST_JSON + "?ticket=" + res["ticket"])
        while True:
            res = json.loads(self.obj.handle_get(TankAPIClient.TEST_STATUS_JSON + "?ticket=" + res["ticket"])[2])
            if res['status'] == TankAPIClient.STATUS_FINISHED:
                break
            time.sleep(1)

        res = json.loads(self.obj.handle_get(TankAPIClient.TEST_STATUS_JSON + "?ticket=" + res["ticket"])[2])
        for artifact in res['artifacts']:
            url = TankAPIClient.DOWNLOAD_ARTIFACT_URL + "?ticket=" + res["ticket"] + "&filename=" + artifact
            self.obj.handle_get(self.obj.handle_get(url))

    def test_run_booking(self):
        res = json.loads(self.obj.handle_get(TankAPIClient.INITIATE_TEST_JSON)[2])
        self.assertNotEquals("", res["ticket"])
        try:
            self.obj.handle_get(TankAPIClient.INITIATE_TEST_JSON + "?exclusive=1")
            self.fail()
        except HTTPError, exc:
            self.assertEqual(423, exc.getcode())

        self.obj.handle_get(TankAPIClient.INTERRUPT_TEST_JSON + "?ticket=" + res["ticket"])
        try:
            self.obj.handle_get(TankAPIClient.INTERRUPT_TEST_JSON + "?ticket=" + res["ticket"])
            self.fail()
        except HTTPError, exc:
            self.assertEqual(422, exc.getcode())


def record_post(handler):
    with open("post.txt", "wb") as fd:
        fd.write(handler.raw_requestline)
        fd.write(str(handler.headers) + "\r\n")
        while True:
            fd.write(handler.rfile.read(1))
            fd.flush()
