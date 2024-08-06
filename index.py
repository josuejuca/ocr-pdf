from flask import Flask, request, redirect, url_for, render_template
import os
import pdfplumber
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'files[]' not in request.files:
        return redirect(request.url)
    files = request.files.getlist('files[]')
    if not files or files[0].filename == '':
        return redirect(request.url)
    
    extracted_info = []
    for file in files:
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            output_text = extract_text_from_pdf(filepath)
            info = extract_important_info(output_text)
            info['filename'] = file.filename
            extracted_info.append(info)
    
    return render_template('result.html', extracted_info=extracted_info)

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_important_info(text):
    info = {}
    
    # Nome da certidão
    certidao_start = text.find("CERTIDÃO JUDICIAL")
    if certidao_start != -1:
        certidao_start += len("CERTIDÃO JUDICIAL")
        certidao_end = text.find("/", certidao_start)
        if certidao_end != -1:
            info['certidao'] = text[certidao_start:certidao_end].strip()
        else:
            info['certidao'] = 'Não encontrado'
    else:
        info['certidao'] = 'Não encontrado'
    
    # Status da certidão
    status_start = text.find("consultando os sistemas processuais abaixo indicados,")
    if status_start != -1:
        status_end = text.find(", até a presente data e hora", status_start)
        if status_end != -1:
            info['status'] = text[status_start + len("consultando os sistemas processuais abaixo indicados,"):status_end].strip()
        else:
            info['status'] = 'Não encontrado'
    else:
        info['status'] = 'Não encontrado'
    
    # Nome da pessoa
    nome_start = text.find("contra:")
    if nome_start != -1:
        nome_start += len("contra:\n")
        nome_end = text.find("\n", nome_start)
        if nome_end != -1:
            info['nome'] = text[nome_start:nome_end].strip().upper()
        else:
            info['nome'] = 'Não encontrado'
    else:
        info['nome'] = 'Não encontrado'
    
    # CPF da pessoa
    cpf_pattern = r"CPF n\.\s*(\d{3}\.\d{3}\.\d{3}-\d{2})"
    match = re.search(cpf_pattern, text)
    if match:
        info['cpf'] = match.group(1)
    else:
        info['cpf'] = 'Não encontrado'
    
    return info

if __name__ == '__main__':
    app.run(debug=True)
