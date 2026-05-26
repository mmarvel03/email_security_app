from gmail_reader import get_latest_unread_email
from flask import Flask, request, render_template
from database import init_db, save_analysis, get_history, get_analysis_by_id, clear_history, get_stats, is_duplicate_analysis
import pickle
import re

app = Flask(__name__)

model = pickle.load(open("model.pkl", "rb"))
vectorizer = pickle.load(open("vectorizer.pkl", "rb"))

trusted_domains = [
    "google.com",
    "accounts.google.com",
    "paypal.com",
    "microsoft.com",
    "amazon.com"
]


def extract_domain(sender):
    match = re.search(r'@([a-zA-Z0-9.-]+)', sender)
    if match:
        return match.group(1).lower()
    return ""


def check_phishing(sender, subject, message, url):
    phishing_score = 0
    reasons = []

    suspicious_words = [
        "verify", "urgent", "account", "login", "bank",
        "password", "click", "confirm", "suspended", "security"
    ]

    suspicious_domains = [
        "secure-login", "verify-account", "bank-alert",
        "paypal-secure", "login-alert", "update-now"
    ]

    sender = sender.lower()
    subject = subject.lower()
    message = message.lower()
    url = url.lower()

    full_text = f"{subject} {message}"
    domain = extract_domain(sender)

    for word in suspicious_words:
        if word in full_text:
            phishing_score += 5
            reasons.append(f"Cuvânt suspect: {word}")

    if url:
        if "@" in url or "-" in url:
            phishing_score += 20
            reasons.append("URL suspect")

        if len(url) > 30:
            phishing_score += 10
            reasons.append("URL prea lung")

        if "bit.ly" in url or "tinyurl" in url or "shorturl" in url:
            phishing_score += 20
            reasons.append("URL prescurtat suspect")

    if sender:
        for suspicious_domain in suspicious_domains:
            if suspicious_domain in sender:
                phishing_score += 25
                reasons.append("Expeditor suspect")

    if any(trusted == domain for trusted in trusted_domains):
        phishing_score -= 15
        reasons.append("Domeniu de încredere detectat")

    if "no-reply@" in sender and "google.com" in domain:
        phishing_score -= 10
        reasons.append("Expeditor automat legitim")

    if "google" in domain and domain != "google.com":
        phishing_score += 25
        reasons.append("Domeniu fals ce imită Google")

    if "paypal" in domain and domain != "paypal.com":
        phishing_score += 25
        reasons.append("Domeniu fals ce imită PayPal")

    if "microsoft" in domain and domain != "microsoft.com":
        phishing_score += 25
        reasons.append("Domeniu fals ce imită Microsoft")

    if phishing_score < 0:
        phishing_score = 0

    return phishing_score, reasons


def analyze_email(sender, subject, message, url):
    combined_text = f"{subject} {message}"
    data = vectorizer.transform([combined_text])
    prediction = model.predict(data)[0]

    phishing_score, reasons = check_phishing(sender, subject, message, url)
    domain = extract_domain(sender)

    if phishing_score >= 40:
        result = "PHISHING"
        score = min(phishing_score, 100)

    elif prediction == 1:
        if any(trusted == domain for trusted in trusted_domains):
            result = "SAFE"
            score = 20
            reasons.append("Expeditor de încredere - posibil fals pozitiv ML")
        else:
            result = "SPAM"
            score = 60

    else:
        result = "SAFE"
        score = 10

    if not is_duplicate_analysis(sender, subject, message, url, result, score):
        save_analysis(sender, subject, message, url, result, score)
        return result, score, reasons


@app.route("/", methods=["GET", "POST"])
def home():
    result = ""
    score = 0
    reasons = []

    sender = ""
    subject = ""
    message = ""
    url = ""

    if request.method == "POST":
        sender = request.form["sender"]
        subject = request.form["subject"]
        message = request.form["message"]
        url = request.form["url"]

        result, score, reasons = analyze_email(sender, subject, message, url)

    history = get_history()
    stats = get_stats()

    return render_template(
        "index.html",
        result=result,
        score=score,
        reasons=reasons,
        sender=sender,
        subject=subject,
        message=message,
        url=url,
        history=history,
        stats=stats
    )


@app.route("/fetch-email", methods=["GET"])
def fetch_email():
    email_data = get_latest_unread_email()

    if not email_data:
        history = get_history()
        stats = get_stats()
        return render_template(
            "index.html",
            result="",
            score=0,
            reasons=[],
            sender="",
            subject="",
            message="",
            url="",
            history=history,
            stats=stats
        )

    sender = email_data["sender"]
    subject = email_data["subject"]
    message = email_data["message"]
    url = email_data["url"]

    result, score, reasons = analyze_email(sender, subject, message, url)

    history = get_history()
    stats = get_stats()

    return render_template(
        "index.html",
        result=result,
        score=score,
        reasons=reasons,
        sender=sender,
        subject=subject,
        message=message,
        url=url,
        history=history,
        stats=stats
    )


@app.route("/clear-history", methods=["POST"])
def clear_history_route():
    clear_history()
    history = get_history()
    stats = get_stats()

    return render_template(
        "index.html",
        result="",
        score=0,
        reasons=[],
        sender="",
        subject="",
        message="",
        url="",
        history=history,
        stats=stats
    )
@app.route("/select-history/<int:analysis_id>", methods=["GET"])
def select_history(analysis_id):
    selected = get_analysis_by_id(analysis_id)

    history = get_history()
    stats = get_stats()

    if not selected:
        return render_template(
            "index.html",
            result="",
            score=0,
            reasons=[],
            sender="",
            subject="",
            message="",
            url="",
            history=history,
            stats=stats
        )

    return render_template(
        "index.html",
        result="",
        score=0,
        reasons=[],
        sender=selected["sender"],
        subject=selected["subject"],
        message=selected["message"],
        url=selected["url"],
        history=history,
        stats=stats
    )

if __name__ == "__main__":
    init_db()
    app.run(debug=True)