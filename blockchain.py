import hashlib
import json
import time
from uuid import uuid4
from typing import Any, Dict, List, Optional
from flask import Flask, jsonify, request, render_template_string


class Blockchain:
    def __init__(self) -> None:
        self.chain: List[Dict[str, Any]] = []
        self.current_transactions: List[Dict[str, Any]] = []
        # Bootstrap Genesis Block
        self.new_block(previous_hash="1", proof=100)

    def new_block(self, proof: int, previous_hash: Optional[str] = None) -> Dict[str, Any]:
        block = {
            "index": len(self.chain) + 1,
            "timestamp": time.time(),
            "transactions": self.current_transactions,
            "proof": proof,
            "previous_hash": previous_hash or self.hash(self.chain[-1]),
        }
        self.current_transactions = []
        self.chain.append(block)
        return block

    def new_transaction(self, sender: str, recipient: str, amount: float) -> int:
        self.current_transactions.append({
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
        })
        return self.last_block["index"] + 1

    @property
    def last_block(self) -> Dict[str, Any]:
        return self.chain[-1]

    @staticmethod
    def hash(block: Dict[str, Any]) -> str:
        block_string = json.dumps(block, sort_keys=True).encode("utf-8")
        return hashlib.sha256(block_string).hexdigest()

    def proof_of_work(self, last_block: Dict[str, Any]) -> int:
        last_proof = last_block["proof"]
        last_hash = self.hash(last_block)
        proof = 0
        while not self.valid_proof(last_proof, proof, last_hash):
            proof += 1
        return proof

    @staticmethod
    def valid_proof(last_proof: int, proof: int, last_hash: str) -> bool:
        guess = f"{last_proof}{proof}{last_hash}".encode("utf-8")
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    def valid_chain(self, chain: List[Dict[str, Any]]) -> bool:
        if not chain:
            return False

        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            if block["previous_hash"] != self.hash(last_block):
                return False
            if not self.valid_proof(last_block["proof"], block["proof"], self.hash(last_block)):
                return False
            last_block = block
            current_index += 1

        return True


app = Flask(__name__)
node_identifier = str(uuid4()).replace("-", "")
blockchain = Blockchain()

# Embedded Single-Page Frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>MicroChain Explorer</title>
  <style>
    :root {
      --bg: #0f172a;
      --card-bg: #1e293b;
      --card-border: #334155;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --primary: #38bdf8;
      --primary-hover: #0ea5e9;
      --green: #22c55e;
      --red: #ef4444;
      --purple: #a855f7;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
    body { background: var(--bg); color: var(--text-main); padding: 2rem 1.5rem; min-height: 100vh; }
    .container { max-width: 1100px; margin: 0 auto; }
    
    header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--card-border); padding-bottom: 1.5rem; margin-bottom: 2rem; }
    h1 { font-size: 1.75rem; font-weight: 700; }
    .badge { padding: 0.35rem 0.8rem; border-radius: 9999px; font-size: 0.85rem; font-weight: 600; display: inline-flex; align-items: center; gap: 0.4rem; }
    .badge-valid { background: rgba(34, 197, 94, 0.15); color: var(--green); border: 1px solid var(--green); }
    .badge-invalid { background: rgba(239, 68, 68, 0.15); color: var(--red); border: 1px solid var(--red); }

    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1.5rem; margin-bottom: 2rem; }
    .card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.5rem; }
    .card h2 { font-size: 1.1rem; margin-bottom: 1rem; color: var(--primary); }

    .form-group { margin-bottom: 0.8rem; }
    label { display: block; font-size: 0.8rem; color: var(--text-muted); margin-bottom: 0.3rem; }
    input { width: 100%; padding: 0.6rem; border-radius: 6px; border: 1px solid var(--card-border); background: #0b1120; color: white; outline: none; }
    input:focus { border-color: var(--primary); }
    
    .actions { display: flex; gap: 0.8rem; flex-wrap: wrap; }
    button { cursor: pointer; border: none; border-radius: 6px; padding: 0.65rem 1.2rem; font-weight: 600; font-size: 0.85rem; transition: background 0.2s; }
    .btn-primary { background: var(--primary); color: #0f172a; }
    .btn-primary:hover { background: var(--primary-hover); }
    .btn-action { background: #334155; color: white; }
    .btn-action:hover { background: #475569; }
    .btn-danger { background: rgba(239, 68, 68, 0.2); color: var(--red); border: 1px solid var(--red); }
    .btn-danger:hover { background: rgba(239, 68, 68, 0.3); }

    .chain-container { display: flex; flex-direction: column; gap: 1.25rem; }
    .block-card { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: 12px; padding: 1.25rem; position: relative; }
    .block-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid var(--card-border); padding-bottom: 0.6rem; margin-bottom: 0.8rem; }
    .block-title { font-weight: bold; font-size: 1.05rem; }
    .block-field { font-size: 0.85rem; margin-bottom: 0.4rem; word-break: break-all; }
    .block-field span { color: var(--text-muted); }
    .hash-tag { font-family: monospace; color: var(--purple); }
    
    .tx-table { width: 100%; margin-top: 0.8rem; border-collapse: collapse; font-size: 0.8rem; }
    .tx-table th, .tx-table td { padding: 0.4rem; text-align: left; border-bottom: 1px solid #273549; }
    .tx-table th { color: var(--text-muted); }
    .chain-link { text-align: center; color: var(--primary); font-size: 1.2rem; margin: -0.5rem 0; }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <div>
        <h1>MicroChain Explorer</h1>
        <p style="color: var(--text-muted); font-size: 0.9rem;">Interactive Local Proof-of-Work Ledger</p>
      </div>
      <div id="status-badge" class="badge badge-valid">● Ledger Intact</div>
    </header>

    <div class="grid">
      <!-- Create Transaction -->
      <div class="card">
        <h2>Submit Transaction to Mempool</h2>
        <div class="form-group">
          <label>Sender</label>
          <input type="text" id="sender" placeholder="e.g. Alice" />
        </div>
        <div class="form-group">
          <label>Recipient</label>
          <input type="text" id="recipient" placeholder="e.g. Bob" />
        </div>
        <div class="form-group">
          <label>Amount</label>
          <input type="number" id="amount" placeholder="e.g. 15.5" />
        </div>
        <button class="btn-primary" onclick="submitTransaction()">Add to Mempool</button>
      </div>

      <!-- Controls -->
      <div class="card">
        <h2>Node Actions</h2>
        <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1rem;">
          Mine unconfirmed mempool transactions or test cryptographic tamper-evidence.
        </p>
        <div class="actions">
          <button class="btn-primary" onclick="mineBlock()">⛏️ Mine Block</button>
          <button class="btn-action" onclick="fetchChain()">🔄 Refresh Ledger</button>
          <button class="btn-danger" onclick="corruptChain()">⚠️ Corrupt Block 2</button>
        </div>
        <div id="action-msg" style="margin-top: 1rem; font-size: 0.85rem; color: var(--text-muted);"></div>
      </div>
    </div>

    <!-- Visual Ledger -->
    <h2 style="font-size: 1.2rem; margin-bottom: 1rem;">Current Blockchain</h2>
    <div id="chain" class="chain-container"></div>
  </div>

  <script>
    async function fetchChain() {
      const res = await fetch('/chain');
      const data = await res.json();
      const valRes = await fetch('/validate');
      const valData = await valRes.json();

      const badge = document.getElementById('status-badge');
      if (valData.is_valid) {
        badge.className = 'badge badge-valid';
        badge.innerText = '● Ledger Intact';
      } else {
        badge.className = 'badge badge-invalid';
        badge.innerText = '✖ Ledger Compromised!';
      }

      const chainEl = document.getElementById('chain');
      chainEl.innerHTML = '';

      data.chain.forEach((b, idx) => {
        if (idx > 0) {
          const arrow = document.createElement('div');
          arrow.className = 'chain-link';
          arrow.innerText = '▲ previous_hash links to ▲';
          chainEl.appendChild(arrow);
        }

        const div = document.createElement('div');
        div.className = 'block-card';

        let txRows = b.transactions.map(t => `
          <tr>
            <td>${t.sender}</td>
            <td>${t.recipient}</td>
            <td><strong>${t.amount}</strong></td>
          </tr>
        `).join('');

        div.innerHTML = `
          <div class="block-header">
            <span class="block-title">Block #${b.index} ${b.index === 1 ? '(Genesis)' : ''}</span>
            <span style="font-size: 0.75rem; color: var(--text-muted);">${new Date(b.timestamp * 1000).toLocaleTimeString()}</span>
          </div>
          <div class="block-field"><span>Proof (Nonce):</span> <strong>${b.proof}</strong></div>
          <div class="block-field"><span>Previous Hash:</span> <span class="hash-tag">${b.previous_hash}</span></div>
          
          <div style="margin-top: 0.8rem;">
            <div style="font-size: 0.8rem; color: var(--text-muted); font-weight: 600;">Transactions (${b.transactions.length})</div>
            ${b.transactions.length > 0 ? `
              <table class="tx-table">
                <thead><tr><th>Sender</th><th>Recipient</th><th>Amount</th></tr></thead>
                <tbody>${txRows}</tbody>
              </table>
            ` : '<div style="font-size: 0.8rem; color: #475569; margin-top: 0.3rem;">No transactions</div>'}
          </div>
        `;
        chainEl.appendChild(div);
      });
    }

    async function submitTransaction() {
      const sender = document.getElementById('sender').value;
      const recipient = document.getElementById('recipient').value;
      const amount = parseFloat(document.getElementById('amount').value);

      if (!sender || !recipient || isNaN(amount)) {
        alert('Please fill out all transaction fields.');
        return;
      }

      const res = await fetch('/transactions/new', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ sender, recipient, amount })
      });
      const data = await res.json();
      document.getElementById('action-msg').innerText = data.message;
      document.getElementById('sender').value = '';
      document.getElementById('recipient').value = '';
      document.getElementById('amount').value = '';
    }

    async function mineBlock() {
      document.getElementById('action-msg').innerText = 'Mining in progress (solving Proof of Work)...';
      const res = await fetch('/mine');
      const data = await res.json();
      document.getElementById('action-msg').innerText = `Mined Block #${data.index} with proof ${data.proof}`;
      fetchChain();
    }

    async function corruptChain() {
      const res = await fetch('/corrupt', { method: 'POST' });
      const data = await res.json();
      document.getElementById('action-msg').innerText = data.message || data.error;
      fetchChain();
    }

    window.onload = fetchChain;
  </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/transactions/new", methods=["POST"])
def new_transaction():
    values = request.get_json(silent=True)
    if not values:
        return jsonify({"error": "Invalid or missing JSON payload"}), 400
    required = ["sender", "recipient", "amount"]
    if not all(k in values for k in required):
        return jsonify({"error": f"Missing required fields. Required: {required}"}), 400
    index = blockchain.new_transaction(values["sender"], values["recipient"], float(values["amount"]))
    return jsonify({"message": f"Transaction queued for Block {index}"}), 201

@app.route("/mine", methods=["GET"])
def mine():
    last_block = blockchain.last_block
    proof = blockchain.proof_of_work(last_block)
    blockchain.new_transaction(sender="0", recipient=node_identifier, amount=1.0)
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)
    return jsonify({
        "message": "New Block Forged",
        "index": block["index"],
        "transactions": block["transactions"],
        "proof": block["proof"],
        "previous_hash": block["previous_hash"],
    }), 200

@app.route("/chain", methods=["GET"])
def full_chain():
    return jsonify({"chain": blockchain.chain, "length": len(blockchain.chain)}), 200

@app.route("/validate", methods=["GET"])
def validate_chain():
    is_valid = blockchain.valid_chain(blockchain.chain)
    return jsonify({
        "is_valid": is_valid,
        "message": "Blockchain ledger is verified and intact." if is_valid else "Blockchain integrity compromised!"
    }), 200

@app.route("/corrupt", methods=["POST"])
def corrupt_chain():
    if len(blockchain.chain) <= 1:
        return jsonify({"error": "Mine at least one block before corrupting."}), 400
    blockchain.chain[1]["transactions"][0]["amount"] = 999999.0
    return jsonify({"message": "Block 2 transaction amount modified to 999999.0"}), 200

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)