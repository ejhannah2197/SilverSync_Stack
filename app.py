from flask import Flask, request, render_template_string

app = Flask(__name__)

HTML_TEMPLATE = '''
<!doctype html>
<title>Message Printer</title>
<h1>Enter a message:</h1>
<form method="post">
    <input name="message" type="text" autofocus>
    <input type="submit" value="Print">
</form>
{% if message %}
    <h2>Your message:</h2>
    <p>{{ message }}</p>
{% endif %}
'''

@app.route('/', methods=['GET', 'POST'])
def index():
        message = ''
        if request.method == 'POST':
                message = request.form.get('message', '')
        return render_template_string(HTML_TEMPLATE, message=message)

if __name__ == '__main__':
        app.run(host='0.0.0.0', port=5000)