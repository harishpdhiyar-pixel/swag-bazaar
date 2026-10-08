# 🚀 स्वैग बाज़ार को 100% FREE में Live कैसे करें (Step-by-Step Guide)

इस गाइड की मदद से आप अपनी वेबसाइट **Swag Bazaar** को बिना कोई पैसा खर्च किए 5 मिनट में इंटरनेट पर लाइव कर सकते हैं और इसका लिंक अपने **Instagram Bio** में डाल सकते हैं!

---

## 🏆 तरीका 1: Render.com पर Live करें (सबसे आसान और बेस्ट)
*Render पर आपको फ्री में 24/7 चलने वाला सर्वर और फ़्री `https://` (SSL Secure) लिंक मिलता है।*

### स्टेप 1: GitHub पर कोड डालें (Free)
1. [GitHub.com](https://github.com) पर जाएं और फ्री अकाउंट बनाएं (अगर पहले से नहीं है)।
2. **"New Repository"** पर क्लिक करें और नाम रखें: `swag-bazaar`
3. इस फोल्डर `C:\Users\HARISH\.gemini\antigravity\scratch\swag-bazaar` की सभी फाइलों को GitHub रिपॉजिटरी में अपलोड (Drag and Drop या Git push) कर दें।
   *(मुख्य फाइलें: `app.py`, `Procfile`, `requirements.txt`, और `templates/` फोल्डर)*

### स्टेप 2: Render.com से कनेक्ट करें
1. [Render.com](https://render.com) पर जाएं और **"Get Started for Free"** पर क्लिक करके अपने GitHub अकाउंट से लॉगिन करें।
2. डैशबोर्ड में ऊपर **"New +"** बटन दबाएं और **"Web Service"** चुनें।
3. अपनी `swag-bazaar` रिपॉजिटरी को चुनें और **"Connect"** करें।

### स्टेप 3: सेटिंग्स भरें (बस इतना ही!):
- **Name:** `swag-bazaar` (या कोई भी नाम)
- **Region:** `Singapore` (भारत के लिए सबसे तेज़ स्पीड)
- **Branch:** `main`
- **Runtime:** `Python 3`
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `gunicorn app:app`
- **Instance Type:** `Free` (₹0 / Month)

4. नीचे **"Create Web Service"** बटन दबाएं!
5. 2 मिनट के अंदर आपकी वेबसाइट लाइव हो जाएगी और आपको लिंक मिल जाएगा जैसे:
   👉 **`https://swag-bazaar.onrender.com`**

---

## ⚡ तरीका 2: Cloudflare Tunnel (तुरंत अपने लैपटॉप/पीसी से Free Live लिंक बनाएं)
*अगर आपको बिना गिटहब के तुरंत अपने फोन और दोस्तों को दिखाने के लिए लाइव लिंक चाहिए:*

1. [Cloudflare Tunnel (cloudflared)](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/) का Windows exe डाउनलोड करें।
2. कमांड प्रॉम्प्ट में यह चलाएं:
   ```cmd
   cloudflared tunnel --url http://localhost:5000
   ```
3. यह आपको तुरंत एक फ्री लाइव HTTPS लिंक दे देगा (उदा. `https://random-words.trycloudflare.com`), जो दुनिया भर में किसी भी मोबाइल पर तुरंत खुल जाएगा!

---

## 🛡️ आपकी वेबसाइट को हैक-प्रूफ (Strong) कैसे बनाया गया है?

आपकी वेबसाइट में निम्नलिखित टॉप-लेवल सिक्योरिटी फीचर्स जोड़ दिए गए हैं:

1. **🔐 क्रिप्टोग्राफिक पिन हैशिंग (PBKDF2/scrypt):**
   - एडमिन पिन डेटाबेस में साधारण टेक्स्ट में नहीं, बल्कि मिलिट्री-ग्रेड क्रिप्टोग्राफिक हैश में सुरक्षित है। अगर कोई डेटाबेस फाइल चुरा भी ले, तो भी पिन नहीं जान सकता।
2. **🚫 ब्रूट-फ़ोर्स प्रोटेक्शन (Brute-Force Lockout):**
   - अगर कोई हैकर या बॉट लगातार 5 बार गलत पिन डालेगा, तो उसका IP एड्रेस 15 मिनट के लिए ब्लॉक (Lock) हो जाएगा।
3. **🛡️ एंटी-स्पैम रेट लिमिटर (Anti-Bot Rate Limiting):**
   - कोई बॉट आपके स्टोर पर फर्जी ऑर्डर्स की बाढ़ नहीं ला सकता (प्रति IP 10 मिनट में सीमित ऑर्डर्स)।
4. **🧼 इनपुट सैनिटाइजेशन (Anti-XSS & SQL Injection Defense):**
   - मोबाइल नंबर में सिर्फ 10 अंक और पिनकोड में सिर्फ 6 अंक ही स्वीकार होते हैं। किसी भी दुर्भावनापूर्ण स्क्रिप्ट या HTML टैग को स्वतः साफ (strip) कर दिया जाता है।
5. **🛡️ सिक्योरिटी HTTP हेडर (Security Armor):**
   - `X-Frame-Options: SAMEORIGIN` (क्लिकजैकिंग रोकता है)
   - `X-Content-Type-Options: nosniff` (MIME स्निफिंग रोकता है)
   - `X-XSS-Protection: 1; mode=block`
6. **🍪 सुरक्षित सेशन कुकीज़:**
   - कुकीज़ `HttpOnly` और `SameSite=Lax` से सुरक्षित हैं, जिससे जावास्क्रिप्ट सेशन नहीं चुरा सकता।
