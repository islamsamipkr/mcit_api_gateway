import json
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

# DEMO ONLY: shared in-memory state is not durable or consistent across Lambda instances.
BALANCE_CENTS = 500000
TRANSACTIONS = []

HTML = '''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>MCIT Mini Bank</title><style>
*{box-sizing:border-box}body{font-family:Arial,sans-serif;background:#f1f5f9;margin:0;color:#17243a}
header{background:#152c55;color:white;padding:24px;text-align:center}main{max-width:850px;margin:28px auto;padding:0 18px}
.hero{background:linear-gradient(110deg,#173e7d,#2674b8);color:white;border-radius:16px;padding:28px}
.hero h1{font-size:42px;margin:8px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:18px;margin:22px 0}
.card{background:white;padding:24px;border-radius:12px;box-shadow:0 3px 12px #0001}
input{width:100%;padding:12px;margin:8px 0;border:1px solid #cbd5e1;border-radius:6px}
button{background:#2563eb;color:white;border:0;padding:12px 18px;border-radius:7px;cursor:pointer}
button:hover{background:#1d4ed8}table{width:100%;border-collapse:collapse}th,td{padding:12px;text-align:left;border-bottom:1px solid #ddd}
#message{margin:16px 0;font-weight:bold}.note{color:#64748b;font-size:13px}@media(max-width:650px){.grid{grid-template-columns:1fr}}
</style></head><body><header><h2>MCIT Mini Bank</h2><div>AWS API Gateway + Lambda Classroom Demo</div></header>
<main><section class="hero"><div>Available balance</div><h1 id="balance">Loading...</h1><div>Fictional account 10001</div></section>
<p id="message" role="status"></p><div class="grid">
<div class="card"><h2>Deposit</h2><input id="deposit" type="number" min="0.01" step="0.01" placeholder="Amount in dollars"><button onclick="transact('deposit')">Deposit</button></div>
<div class="card"><h2>Withdraw</h2><input id="withdraw" type="number" min="0.01" step="0.01" placeholder="Amount in dollars"><button onclick="transact('withdraw')">Withdraw</button></div></div>
<div class="card"><h2>Recent transactions</h2><button onclick="loadBalance()">Refresh balance</button>
<table><thead><tr><th>Time (UTC)</th><th>Type</th><th>Amount</th></tr></thead><tbody id="rows"></tbody></table></div>
<p class="note">Educational demo only. No real funds. Lambda memory can reset between requests.</p></main>
<script>
const API_URL = '/api';
const dollars = cents => (cents/100).toLocaleString('en-US',{style:'currency',currency:'USD'});
async function request(action,amount){
  const response=await fetch(API_URL,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action,amount})});
  const data=await response.json();if(!response.ok)throw Error(data.error||'Request failed');return data;
}
function render(data){
 document.getElementById('balance').textContent=dollars(data.balance_cents);
 const tbody=document.getElementById('rows');tbody.replaceChildren();
 for(const tx of data.transactions){const tr=tbody.insertRow();
 for(const value of [tx.time,tx.type,dollars(tx.amount_cents)]){const td=tr.insertCell();td.textContent=value;}}
}
async function loadBalance(){try{render(await request('balance'));}catch(e){document.getElementById('message').textContent=e.message;}}
async function transact(action){
 const input=document.getElementById(action);const amount=input.value;
 if(!/^\\d+(\\.\\d{1,2})?$/.test(amount)||Number(amount)<=0){document.getElementById('message').textContent='Enter a positive amount (max 2 decimals).';return;}
 try{const data=await request(action,amount);render(data);document.getElementById('message').textContent=data.message;input.value='';}
 catch(e){document.getElementById('message').textContent=e.message;}
}
loadBalance();
</script></body></html>'''


def reply(status, content, content_type='application/json'):
    return {'statusCode': status, 'headers': {'Content-Type': content_type, 'Cache-Control': 'no-store'},
            'body': content if isinstance(content, str) else json.dumps(content)}


def snapshot(message=None):
    data = {'account': '10001', 'balance_cents': BALANCE_CENTS, 'transactions': TRANSACTIONS}
    if message:
        data['message'] = message
    return data


def lambda_handler(event, context):
    global BALANCE_CENTS
    http = event.get('requestContext', {}).get('http', {})
    method, path = http.get('method', 'GET'), event.get('rawPath', '/')
    print('Method:', method, 'Path:', path)
    if method == 'GET' and path in ('/', ''):
        return reply(200, HTML, 'text/html; charset=utf-8')
    if method != 'POST' or path != '/api':
        return reply(404, {'error': 'Route not found', 'method': method, 'path': path})
    try:
        payload = json.loads(event.get('body') or '{}')
        if not isinstance(payload, dict):
            return reply(400, {'error': 'Expected JSON object'})
        action = payload.get('action')
        if action == 'balance':
            return reply(200, snapshot())
        if action not in ('deposit', 'withdraw'):
            return reply(400, {'error': 'Unknown action'})
        raw = payload.get('amount')
        if not isinstance(raw, str):
            return reply(400, {'error': 'Amount must be a string'})
        try:
            amount = Decimal(raw)
        except InvalidOperation:
            return reply(400, {'error': 'Invalid amount'})
        if not amount.is_finite() or amount <= 0 or amount.as_tuple().exponent < -2:
            return reply(400, {'error': 'Use a positive amount with at most 2 decimals'})
        cents = int(amount * 100)
        if cents > 100000000:
            return reply(400, {'error': 'Amount exceeds classroom limit'})
        if action == 'withdraw' and cents > BALANCE_CENTS:
            return reply(400, {'error': 'Insufficient funds'})
        BALANCE_CENTS += cents if action == 'deposit' else -cents
        TRANSACTIONS.insert(0, {'time': datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M'),
                                'type': action.title(), 'amount_cents': cents})
        del TRANSACTIONS[20:]
        return reply(200, snapshot(action.title() + ' successful'))
    except (ValueError, TypeError):
        return reply(400, {'error': 'Invalid JSON'})
