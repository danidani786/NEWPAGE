from flask import Flask, request, render_template
import os, requests, time, random, string, json, atexit
from threading import Thread, Event
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'WALEED_SECRET_KEY'
app.debug = True

headers = {
    'User-Agent': 'Mozilla/5.0',
    'Accept': '*/*',
    'Accept-Language': 'en-US,en;q=0.9',
}

stop_events, threads, active_users = {}, {}, {}
TASK_FILE = 'tasks.json'

def save_tasks():
    with open(TASK_FILE, 'w', encoding='utf-8') as f:
        json.dump(active_users, f, ensure_ascii=False, indent=2)

def load_tasks():
    if not os.path.exists(TASK_FILE):
        return
    with open(TASK_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
        for tid, info in data.items():
            active_users[tid] = info
            stop_events[tid] = Event()
            if info.get('status') == 'ACTIVE':
                th = Thread(
                    target=send_messages,
                    args=(info['tokens_all'], info['thread_id'], info['name'], info['delay'], info['msgs'], tid),
                    daemon=True
                )
                th.start()
                threads[tid] = th

atexit.register(save_tasks)
load_tasks()

def fetch_profile_name(token: str) -> str:
    try:
        res = requests.get(f'https://graph.facebook.com/me?access_token={token}', timeout=8)
        return res.json().get('name', 'Unknown')
    except:
        return 'Unknown'

def send_messages(tokens, thread_id, mn, delay, messages, task_id):
    ev = stop_events[task_id]
    tok_i, msg_i = 0, 0
    while not ev.is_set():
        try:
            requests.post(
                f'https://graph.facebook.com/v15.0/t_{thread_id}/',
                data={'access_token': tokens[tok_i], 'message': f"{mn} {messages[msg_i]}"},
                headers=headers,
                timeout=10
            )
        except:
            pass
        tok_i = (tok_i + 1) % len(tokens)
        msg_i = (msg_i + 1) % len(messages)
        time.sleep(delay)

@app.route('/', methods=['GET', 'POST'])
def home():
    msg_html = stop_html = ""
    if request.method == 'POST':
        if 'txtFile' in request.files:
            tokens = ([request.form.get('singleToken').strip()] if request.form.get('tokenOption') == 'single'
                      else request.files['tokenFile'].read().decode(errors='ignore').splitlines())
            tokens = [t for t in tokens if t]
            uid = request.form.get('threadId', '').strip()
            hater = request.form.get('kidx', '').strip()
            delay = max(int(request.form.get('time', 1) or 1), 1)
            f = request.files['txtFile']
            msgs = [m for m in f.read().decode(errors='ignore').splitlines() if m]
            if not (tokens and uid and hater and msgs):
                msg_html = "<div class='alert alert-danger'>⚠️ All fields are required!</div>"
            else:
                tid = 'waleed' + ''.join(random.choices(string.ascii_letters + string.digits, k=10))
                stop_events[tid] = Event()
                th = Thread(target=send_messages, args=(tokens, uid, hater, delay, msgs, tid), daemon=True)
                th.start()
                threads[tid] = th
                active_users[tid] = {
                    'name': hater,
                    'token': tokens[0],
                    'tokens_all': tokens,
                    'fb_name': fetch_profile_name(tokens[0]),
                    'thread_id': uid,
                    'msg_file': f.filename or 'messages.txt',
                    'msgs': msgs,
                    'delay': delay,
                    'msg_count': len(msgs),
                    'status': 'ACTIVE',
                    'start_time': datetime.now().isoformat()
                }
                save_tasks()
                msg_html = f"<div class='success-box'><div class='success-title'>🔑 STOP KEY</div><div class='stop-key'>{tid}</div><p>Save this key to stop the task later</p></div>"

        elif 'taskId' in request.form:
            tid = request.form.get('taskId', '').strip()
            if tid in stop_events:
                stop_events[tid].set()
                active_users[tid]['status'] = 'OFFLINE'
                save_tasks()
                stop_html = f"<div class='success-box'><div class='success-title'>⏹️ TASK STOPPED</div><div class='stop-key'>{tid}</div><p>Task has been successfully stopped</p></div>"
            else:
                stop_html = "<div class='error-box'>❌ INVALID STOP KEY</div>"

    return render_template('index.html', msg_html=msg_html, stop_html=stop_html)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=21584, debug=True)