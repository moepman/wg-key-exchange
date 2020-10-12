import re
import atexit
import logging

from flask import Flask, abort, jsonify, render_template, request
from voluptuous import Invalid, MultipleInvalid, Required, Schema
import zmq

from wgkex.config import load_config

app = Flask(__name__)
config = load_config()

WG_PUBKEY_PATTERN = re.compile(r"^[A-Za-z0-9+/]{42}[AEIMQUYcgkosw480]=$")


def is_valid_wg_pubkey(pubkey):
    if WG_PUBKEY_PATTERN.match(pubkey) is None:
        raise Invalid("Not a valid Wireguard public key")
    return pubkey


def is_valid_domain(domain):
    if domain not in config.get("domains"):
        raise Invalid("Not a valid domain")
    return domain


WG_KEY_EXCHANGE_SCHEMA_V1 = Schema(
    {Required("public_key"): is_valid_wg_pubkey, Required("domain"): is_valid_domain}
)

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")


@app.route("/", methods=["GET"])
def index():
    # return templates/index.html
    return render_template("index.html")


@app.route("/api/v1/wg/key/exchange", methods=["POST"])
def wg_key_exchange():
    try:
        data = WG_KEY_EXCHANGE_SCHEMA_V1(request.get_json(force=True))
    except MultipleInvalid as ex:
        return abort(400, jsonify({"error": {"message": str(ex)}}))

    key = data["public_key"]
    domain = data["domain"]
    logging.debug(f"Received WG Key for domain {domain}: {key}")

    socket.send_string(f"{key}, {domain}")
    message = socket.recv_string()
    print(f"Got {message}")

    return jsonify({"Message": "OK"}), 200
