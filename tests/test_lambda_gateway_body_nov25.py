"""API Gateway request decoding rejects malformed payloads before routing."""
import base64
import unittest

from app import MAX_JSON_BYTES, lambda_handler


def post_event(body, *, encoded=False):
    return {
        "requestContext": {"http": {"method": "POST"}},
        "rawPath": "/not-a-route",
        "body": body,
        "isBase64Encoded": encoded,
    }


class LambdaGatewayBodyTests(unittest.TestCase):
    def test_valid_base64_json_reaches_normal_route_handling(self):
        raw = b'{"safe":true}'
        event = post_event(base64.b64encode(raw).decode("ascii"), encoded=True)
        response = lambda_handler(event, None)
        self.assertEqual(response["statusCode"], 404)
        self.assertEqual(response["headers"]["Cache-Control"], "no-store")

    def test_invalid_base64_and_invalid_utf8_fail_as_bad_requests(self):
        malformed = lambda_handler(post_event("a!$=" , encoded=True), None)
        invalid_utf8 = lambda_handler(
            post_event(base64.b64encode(b"\xff").decode("ascii"), encoded=True),
            None,
        )
        self.assertEqual(malformed["statusCode"], 400)
        self.assertEqual(invalid_utf8["statusCode"], 400)

    def test_decoded_base64_payload_is_subject_to_the_same_byte_limit(self):
        oversized = base64.b64encode(b" " * (MAX_JSON_BYTES + 1)).decode("ascii")
        response = lambda_handler(post_event(oversized, encoded=True), None)
        self.assertEqual(response["statusCode"], 413)
        self.assertIn("16 KB", response["body"])

    def test_plain_payload_limit_is_measured_in_utf8_bytes(self):
        response = lambda_handler(post_event("x" * (MAX_JSON_BYTES + 1)), None)
        self.assertEqual(response["statusCode"], 413)

    def test_non_string_gateway_body_is_rejected(self):
        response = lambda_handler(post_event({"unexpected": "object"}), None)
        self.assertEqual(response["statusCode"], 400)


if __name__ == "__main__":
    unittest.main()
