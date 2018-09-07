import json  # A nice format for our block data
import time  # For timestamps
from hashlib import sha256  # The hash algorithm used
from flask import Flask, request # For the web page without a server
import requests # To...


class Block:
    def __init__(self, index, txs, timestamp, previousHash):
        self.index = index                    # Number of this block in the chain
        self.txs = txs                      # The data the block contains
        self.timestamp = timestamp          # Time block was created
        self.previousHash = previousHash    # The hash of the last block, for validation
        self.nonce = 0

    def makeHash(self):
        """
        Returns the hash of a given Block
        """
        # Make a JSON string out of the block
        blockString = json.dumps(self.__dict__, sort_keys=True)
        # Hash that string and return it in hex
        return sha256(blockString.encode()).hexdigest()


class Blockchain:
    difficulty = 2  # difficulty for Proof of Work

    def __init__(self):
        self.unconfirmedTxs = []            # data not yet populated
        self.chain = []                     # an empty chain
        self.createGenesis()                # add a genesis block to kick things off

    def createGenesis(self):
        """
        Generates a genesis block (the first block in a chain) and appends
        it to the chain. The genesis block has index 0, previousHash 0,
        and a valid hash.
        """
        # Genesis block parameters
        genesisBlock = Block(0, [], time.time(), "0")
        genesisBlock.hash = genesisBlock.makeHash()     # Hash the block
        self.chain.append(genesisBlock)                 # Add it to the chain

    @property
    def lastBlock(self):
        return self.chain[-1]  # Gets the previous block in the chain

    def proofOfWork(self, block):
        """
        Tries different nonces until hash satisfies difficulty criteria
        """

        tmpHash = block.makeHash()  # lets try a hash

        # does this hash satisfy the difficulty requirements?...
        while not tmpHash.startswith('0'*Blockchain.difficulty):
            block.nonce += 1  # if not, try a new nonce
            tmpHash = block.makeHash()  # and a new hash with it

        return tmpHash  # Success!

    def addBlock(self, block, proof):
        """
        Adds a block to the chain if it is valid
        """
        previousHash = self.lastBlock.hash

        # If the previous hash/block is incorrect...
        if previousHash != block.previousHash:
            return False  # Invalid block

        # If this block does not hash to something valid...
        if not self.isValidProof(block, proof):
            return False  # then it's invalid

        block.hash = proof
        self.chain.append(block)
        return True  # Success!

    def addNewTx(self, tx):
        # Put your tx into the "mempool"
        self.unconfirmedTxs.append(tx)

    def mine(self):
        """
        Attempts to add new txs to the blockchain by finding valid
        proofs of work for new blocks that contain them
        """
        if not self.unconfirmedTxs:  # No txs to add?...
            return False  # Then there's no need to work

        lastBlock = self.lastBlock # Grb the most recent block

        newBlock = Block(index=lastBlock.index + 1,  # A new block
                         txs=self.unconfirmedTxs,  # Mempool data is added to block
                         timestamp=time.time(),
                         previousHash=lastBlock.hash)

        proof = self.proofOfWork(newBlock)  # Find the valid hash
        # Add the new, valid, block containing txs
        self.addBlock(newBlock, proof)
        self.unconfirmedTxs = []  # Clear the mempool
        return newBlock.index  # Success!

    @classmethod
    def checkChainValidity(cls, chain):
        """
        Will run through the chain block by block in order to determine validity of the blockchain
        """
        result = True
        previousHash = 0

        for block in chain:
            blockHash = block.hash
            delattr(block, "hash")  # remove the hash so it can be checked

            if not cls.isValidProof(block, block.hash) or \
                    previousHash != block.previousHash:
                result = False
                break

            block.hash, previousHash = blockHash, blockHash

        return result

    @classmethod
    def isValidProof(cls, block, propHash):
        """
        Checks that the proposed hash value is actually the hash value
        and that it satisfies the difficulty requirement
        """
        return (propHash.startswith('0'*Blockchain.difficulty) and  # Difficulty check
                propHash == block.makeHash())  # Validity of hash check

"""
ABANDON HOPE ALL YE WHO ENTER HERE
I do not know flask.
I literally copied this code.
Please say thank you to Satwik Kansal at IBM for making this tutorial
"""

app = Flask(__name__)  # Make a new flask app
blockchain = Blockchain()  # The local copy of the blockchain
peers = set()  # Create a set to start storing peers


@app.route('/newTx', methods=['POST'])
def newTx():
    txData = request.get_json(force=True)
    reqFields = ["author", "content"]

    for field in reqFields:
        if not txData.get(field):
            return "Invalid Transaction Data.", 404

    txData["timestamps"] = time.time()

    blockchain.addNewTx(txData)

    return "Success", 201  # !!!


@app.route('/chain', methods=['GET'])
def getChain():
    chainData = []

    for block in blockchain.chain:
        chainData.append(block.__dict__)

    return json.dumps({"length": len(chainData),
                       "chain": chainData})


@app.route('/mine', methods=['GET'])
def mineUnconfirmedTxs():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine."
    announceNewBlock(result)
    return "Block #{} has been mined.".format(result)


@app.route('/pendingTxs')
def getPendingTxs():
    return json.dumps(blockchain.unconfirmedTxs)


@app.route('/addNodes', methods=['POST'])
def registerNewPeers():
    nodes = request.get_json(force=True)
    if not nodes:
        return("Invalid data.", 400)
    else:
        for node in nodes:
            peers.add(node)

    return "Success", 201


@app.route('/addBlock', methods=['POST'])
def validateAndAddBlock():
    blockData = request.get_json(force=True)
    block = Block(blockData["index"],
                  blockData["transactions"],
                  blockData["timestamp"],
                  blockData["previousHash"])

    proof = blockData['hash']
    added = blockchain.addBlock(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201


def announceNewBlock(block):
    for peer in peers:
        url = "http://{}/addBlock".format(peer)
        requests.post(url, data=json.dumps(block.__dict__, sort_keys=True))


def consensus():
    """
    A simple consensus algorithm that chooses the longest chain if chains differ
    This is done because it is likely that the longest chain has the most work done on it
    If a longer chain is found, that chain replaces ours
    """
    global blockchain

    longestChain = None
    currentLen = len(blockchain)

    for node in peers:  # cycle through all peers and...
        # Get the chain from a peer
        response = requests.get('http://{}/chain'.format(node))
        responseLen = response.json()['length']  # Get that chains length
        responseChain = response.json()['chain']  # Get the chain itself

        # If the response is longer and valid, it's a candidate new chain
        if responseLen > currentLen and blockchain.checkChainValidity(responseChain):
            currentLen = responseLen
            longestChain = responseChain

    if longestChain:
        blockchain = longestChain
        return True
    else:
        return False


app.run(debug=True, port=8000)
