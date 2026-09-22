*{
    margin:0;
    padding:0;
    box-sizing:border-box;
}

body{
    background:#f5f7fb;
    font-family:Segoe UI,Arial,sans-serif;
    padding:20px;
}

.container{
    display:grid;
    grid-template-columns:2fr 1fr;
    gap:20px;
}

.card{
    background:#fff;
    border:1px solid #e6ebf2;
    border-radius:18px;
    padding:20px;
}

.title{
    font-size:20px;
    font-weight:600;
    margin-bottom:20px;
    color:#1f2937;
}

label{
    display:block;
    margin-top:14px;
    margin-bottom:6px;
    font-size:14px;
    font-weight:600;
}

input,
textarea{
    width:100%;
    border:1px solid #dbe2ea;
    border-radius:12px;
    padding:12px;
    font-size:14px;
}

textarea{
    resize:none;
}

.row{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:15px;
}

.stats{
    display:grid;
    grid-template-columns:1fr 1fr;
    gap:12px;
    margin-top:15px;
}

.stat{
    border:1px solid #dde4ee;
    border-radius:14px;
    text-align:center;
    padding:20px;
}

.stat h4{
    color:#94a3b8;
    font-size:12px;
}

.stat span{
    font-size:28px;
    font-weight:700;
    margin-top:10px;
    display:block;
}

.send-btn{
    width:100%;
    margin-top:15px;
    height:52px;
    border:none;
    border-radius:14px;
    background:#2563eb;
    color:#fff;
    font-size:16px;
    font-weight:600;
    cursor:pointer;
}

.send-btn:hover{
    background:#1d4ed8;
}

.status{
    margin-top:15px;
    padding:10px;
    border-radius:10px;
    background:#eef6ff;
    color:#1e40af;
    text-align:center;
}

.email-count{
    font-size:14px;
    margin-top:10px;
    color:#64748b;
}
