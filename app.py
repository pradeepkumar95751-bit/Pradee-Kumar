<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Bulk Email Sender</title>
    <link rel="stylesheet" href="style.css">
</head>
<body>
    <div class="container">
        <header>
            <h1>Bulk Email Sender</h1>
        </header>

        <div class="main-content">
            <div class="left-panel">
                <section class="card">
                    <h2>Compose Message</h2>
                    <div class="input-group">
                        <input type="email" placeholder="Your Gmail">
                        <input type="password" placeholder="16-char app password">
                    </div>
                    <div class="input-group">
                        <input type="text" placeholder="Sender Name">
                        <input type="text" placeholder="Email Subject">
                    </div>
                    <textarea placeholder="Write your email here..."></textarea>
                </section>
            </div>

            <div class="right-panel">
                <section class="card">
                    <h2>Recipients</h2>
                    <textarea placeholder="Paste emails (comma separated, new lines, etc.)"></textarea>
                </section>

                <section class="card monitor">
                    <h2>Progress Monitor</h2>
                    <div class="stats">
                        <div class="stat-box"><span>TOTAL</span><p id="total">0</p></div>
                        <div class="stat-box"><span>SENT</span><p id="sent">0</p></div>
                        <div class="stat-box failed"><span>FAILED</span><p id="failed">0</p></div>
                        <div class="stat-box"><span>REMAINING</span><p id="rem">0</p></div>
                    </div>
                    <div class="progress-bar"><div class="fill"></div></div>
                    <button class="btn-send">Send All</button>
                </section>

                <section class="card log">
                    <h2>Live Delivery Log</h2>
                    <div class="log-area">Waiting to start sending...</div>
                </section>
            </div>
        </div>
    </div>
</body>
</html>
