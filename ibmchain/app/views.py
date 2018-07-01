import datetime
import json

import requests
from flask import redirect, render_template, request

from app import app

CONNECTED_NODE_ADDRESS = "http://127.0.0.1:8000"

posts = []


def fetchPosts():
    # Gets the local chain address
    getChainAddress = "{}/chain".format(CONNECTED_NODE_ADDRESS)
    # Stores the chain
    response = requests.get(getChainAddress)

    if response.status_code == 200:  # If we get a valid response...
        content = []  # ready to get the block data
        chain = json.loads(response.content)  # Extracts the chain itself
        for block in chain["chain"]:
            for tx in block["txs"]:
                tx["index"] = block["index"]
                tx["hash"] = block["previousHash"]
                tx["timestamp"] = block["timestamp"]
                content.append(tx)  # Make a local content entry

        global posts

        # puts contents into posts, sorted chronologically
        posts = sorted(content, key=lambda k: k['timestamp'], reverse=True)


@app.route('/')
def index():
    fetchPosts()
    return render_template('index.html',
                           title='YourNet: Decentralized '
                                 'content sharing',
                           posts=posts,
                           node_address=CONNECTED_NODE_ADDRESS,
                           readable_time=timestampToString)


@app.route('/submit', methods=['POST'])
def submitTextarea():
    """
    Endpoint for new transactins via application
    """
    postContent = request.form["content"]
    author = request.form["author"]

    postObject = {
        'author': author,
        'content': postContent,
    }

    # Submit a new transaction
    newTxAddress = "{}/newTx".format(CONNECTED_NODE_ADDRESS)

    requests.post(newTxAddress, json=postObject, headers={
                  'Content-type': 'application/json'})

    return redirect('/')


def timestampToString(epoch_time):
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%H:%M')
