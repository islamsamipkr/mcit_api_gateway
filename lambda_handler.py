
import json
import base64
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

# Classroom demo only.
# Lambda memory is NOT reliable persistent storage.
INITIAL_BALANCE = 500000  # $5,000.00 in cents
balance = INITIAL_BALANCE
transactions = []


HTML_PAGE = r"""
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>MCIT Mini Bank</title>
<style>
* { box-sizing: border-box; }
body {
  margin: 0;
  font-family: Arial, sans-serif;
  background: #f1f5f9;
  color: #172033;
}
header {
  background: #142b50;
  color: white;
  padding: 22px 30px;
}
header h1 { margin: 0; font-size: 25px; }
header p { margin: 7px 0 0; color: #cbd5e1; }
.container {
  max-width: 900px;
  margin: 35px auto;
  padding: 0 18px;
}
.balance-card {
  background: linear-gradient(125deg, #183a73, #2867b2);
  color: white;
  padding: 32px;
  border-radius: 16px;
  box-shadow: 0 8px 24px #17255422;
}
.balance-card p { color: #dbeafe; }
.balance {
  font-size: 40px;
  font-weight: bold;
  margin: 15px 0;
}
.grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 20px;
  margin-top: 24px;
}
.card {
  background: white;
  border-radius: 14px;
  padding: 25px;
  box-shadow: 0 4px 15px #0000000a;
}
.card h2 { margin-top: 0; font-size: 21px; }
input {
  width: 100%;
  padding: 13px;
  border: 1px solid #cbd5e1;
  border-radius: 7px;
  font-size: 16px;
}
button {
  margin-top: 14px;
  background: #2563eb;
  color: white;
  border: 0;
  border-radius: 7px;
  padding: 13px 20px;
  cursor: pointer;
  font-weight: bold;
}
button:hover { background: #1d4ed8; }
.withdraw { background: #e15a35; }
.withdraw:hover { background: #b93f23; }
.refresh { background: #475569; }
.message {
  padding: 12px;
  margin-top: 18px;
  border-radius: 7px;
  display: none;
}
.success { background: #dcfce7; color: #166534; }
.error { background: #fee2e2; color: #991b1b; }
table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 15px;
}
th, td {
  padding: 13px;
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
}
th { background: #f8fafc; }
.credit { color: #15803d; font-weight: bold; }
.debit { color: #dc2626; font-weight: bold; }
.note { color: #64748b; font-size: 13px; }
@media(max-width: 650px) {
  .grid { grid-template-columns: 1fr; }
  .balance { font-size: 32px; }
}
</style>
</head>
<body>

<header>
  <h1>MCIT Mini Bank</h1>
  <p>Serverless Banking Portal | AWS API Gateway + Lambda</p>
</header>

<div class="container">
  <div class="balance-card">
    <p>Available Balance</p>
    <div class="balance" id="balance">Loading...</div>
    <p>Demo Account: 10001</p>
    <button class="refresh" onclick="loadAccount()">
      Refresh Balance
    </button>
  </div>

  <div id="message" class="message" role="status"></div>

  <div class="grid">
    <div class="card">
      <h2>Deposit Money</h2>
      <p>Enter amount to deposit</p>
      <input type="number" id="depositAmount"
             placeholder="Amount ($)" min="0.01"
             step="0.01">
      <button onclick="sendTransaction('deposit')">
        Deposit
      </button>
    </div>

    <div class="card">
      <h2>Withdraw Money</h2>
      <p>Enter amount to withdraw</p>
      <input type="number" id="withdrawAmount"
             placeholder="Amount ($)" min="0.01"
             step="0.01">
      <button class="withdraw"
              onclick="sendTransaction('withdraw')">
        Withdraw
      </button>
    </div>
  </div>

  <div class="card" style="margin-top:24px">
    <h2>Transaction History</h2>
    <table>
      <thead>
        <tr>
          <th>Date</th>
          <th>Type</th>
          <th>Amount</th>
        </tr>
      </thead>
      <tbody id="transactionTable"></tbody>
    </table>
    <p class="note">
      Educational demo only. No real money is involved.
      Lambda memory may reset between requests.
    </p>
  </div>
</div>

<script>
const API_URL = "/newdeployment/api";

function money(cents) {
  return "$" + (cents / 100).toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  });
}

function showMessage(text, isError = false) {
  const box = document.getElementById("message");
  box.textContent = text;
  box.className = "message " + (isError ? "error" : "success");
  box.style.display = "block";
}

async function callAPI(action, amount = null) {
  const response = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, amount })
  });

  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Request failed");
  }

  return data;
}

function renderAccount(data) {
  document.getElementById("balance").textContent =
    money(data.balance_cents);

  const table = document.getElementById("transactionTable");
  table.replaceChildren();

  if (!data.transactions.length) {
    const row = table.insertRow();
    const cell = row.insertCell();
    cell.colSpan = 3;
    cell.textContent = "No transactions yet.";
    return;
  }

  data.transactions.forEach(tx => {
    const row = table.insertRow();

    const date = row.insertCell();
    date.textContent = tx.date;

    const type = row.insertCell();
    type.textContent = tx.type;

    const amount = row.insertCell();
    amount.textContent =
      (tx.type === "Deposit" ? "+" : "-") +
      money(tx.amount_cents);

    amount.className =
      tx.type === "Deposit" ? "credit" : "debit";
  });
}

async function loadAccount() {
  try {
    const data = await callAPI("balance");
    renderAccount(data);
  } catch (error) {
    showMessage(error.message, true);
  }
}

async function sendTransaction(action) {
  const field = document.getElementById(
    action === "deposit" ? "depositAmount" : "withdrawAmount"
  );

  const amount = field.value.trim();

  if (!/^\d+(\.\d{1,2})?$/.test(amount) ||
      Number(amount) <= 0) {
    showMessage("Enter a valid positive amount.", true);
    return;
  }

  try {
    const data = await callAPI(action, amount);
    renderAccount(data);
    showMessage(data.message);
    field.value = "";
  } catch (error) {
    showMessage(error.message, true);
  }
}

loadAccount();
</script>
</body>
</html>
"""


def response(status, body, content_type="application/json"):
    return {
        "statusCode": status,
        "headers": {
            "Content-Type": content_type,
            "Cache-Control": "no-store"
        },
        "body": body if isinstance(body, str) else json.dumps(body)
    }


def account_data(message=None):
    result = {
        "account": "10001",
        "balance_cents": balance,
        "transactions": transactions
    }
    if message:
        result["message"] = message
    return result


def handle_bank_request(event):
    global balance

    try:
        raw_body = event.get("body") or "{}"

        if event.get("isBase64Encoded"):
            raw_body = base64.b64decode(raw_body).decode("utf-8")

        data = json.loads(raw_body)

        if not isinstance(data, dict):
            return response(400, {"error": "Expected a JSON object"})

        action = data.get("action")

        if action == "balance":
            return response(200, account_data())

        if action not in ("deposit", "withdraw"):
            return response(400, {"error": "Invalid action"})

        raw_amount = data.get("amount")

        if not isinstance(raw_amount, str):
            return response(400, {"error": "Amount must be a string"})

        try:
            amount = Decimal(raw_amount)
        except InvalidOperation:
            return response(400, {"error": "Invalid amount"})

        if not amount.is_finite() or amount <= 0:
            return response(400, {"error": "Amount must be positive"})

        if amount.as_tuple().exponent < -2:
            return response(400, {"error": "Maximum two decimal places"})

        amount_cents = int(amount * 100)

        if amount_cents > 100000000:
            return response(400, {"error": "Amount exceeds demo limit"})

        if action == "withdraw" and amount_cents > balance:
            return response(400, {"error": "Insufficient funds"})

        if action == "deposit":
            balance += amount_cents
            tx_type = "Deposit"
        else:
            balance -= amount_cents
            tx_type = "Withdrawal"

        transactions.insert(0, {
            "date": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"
            ),
            "type": tx_type,
            "amount_cents": amount_cents
        })

        del transactions[20:]

        return response(
            200,
            account_data(tx_type + " successful!")
        )

    except (ValueError, UnicodeDecodeError):
        return response(400, {"error": "Invalid JSON request"})
    except Exception:
        print("Bank request failed")
        return response(500, {"error": "Internal server error"})



def lambda_handler(event, context):
    http = event.get("requestContext", {}).get("http", {})

    method = http.get("method", "GET")
    path = event.get("rawPath", "/")

    # Support named API Gateway stage
    stage = event.get("requestContext", {}).get("stage", "")

    if stage and stage != "$default":
        prefix = "/" + stage
        if path == prefix:
            path = "/"
        elif path.startswith(prefix + "/"):
            path = path[len(prefix):]

    # Remove trailing slash except root
    if path != "/":
        path = path.rstrip("/")

    print("Method:", method)
    print("Path:", path)
    print("Stage:", stage)

    # Serve banking frontend
    if method == "GET" and path == "/":
        return response(
            200,
            HTML_PAGE,
            "text/html; charset=utf-8"
        )

    # Handle banking operations
    if method == "POST" and path == "/api":
        return handle_bank_request(event)

    return response(
        404,
        {
            "error": "Route not found",
            "method": method,
            "path": path
        }
    )
