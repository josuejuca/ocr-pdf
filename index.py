from flask import Flask, request, redirect, url_for, render_template, send_file
import os
import pdfplumber
import re
import pandas as pd
from datetime import datetime

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
    
    # Save to Excel
    df = pd.DataFrame(extracted_info)
    filename = f'avaliacao-{datetime.today().strftime("%d-%m-%Y")}.xlsx'
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    df.to_excel(filepath, index=False)

    return render_template('result.html', extracted_info=extracted_info, filename=filename)

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def extract_important_info(text):
    # Civel, criminal, eleitoral 
    if "CERTIDÃO JUDICIAL" in text:
        return extract_judicial_cert_info(text)
    # SEFAZ
    elif "CERTIDÃO NEGATIVA DE DÉBITOS" in text or "CERTIDÃO POSITIVA DE DÉBITOS COM EFEITO DE NEGATIVA" in text:
        return extract_sefaz_cert_info(text)
    # Falencia 
    elif "AÇÕES DE FALÊNCIAS E RECUPERAÇÕES JUDICIAIS" in text or "AÇÕES DE FALÊNCIAS E RECUPERAÇÕES JUDICIAIS" in text:
        return extract_falencia_cert_info(text)
    # Especial
    elif "ESPECIAL - AÇÕES CÍVEIS E CRIMINAIS" in text or "ESPECIAL - AÇÕES CÍVEIS E CRIMINAIS" in text:
        return extract_especial_cert_info(text)
    # Receita 
    elif "CERTIDÃO NEGATIVA DE DÉBITOS RELATIVOS AOS TRIBUTOS FEDERAIS" in text or "CERTIDÃO POSITIVA COM EFEITOS DE NEGATIVA DE DÉBITOS RELATIVOS AOS TRIBUTOS" in text:
        return extract_receita_cert_info(text)
    # trabalhista 
    elif "CERTIDÃO DE AÇÕES TRABALHISTAS" in text or "CERTIDÃO POSITIVA DE DÉBITOS TRABALHISTAS" in text:
        return extract_trabalhista_cert_info(text)
    else:
        return {
            'certidao': 'Tipo de certidão não reconhecido',
            'status': 'Não encontrado',
            'nome': 'Não encontrado',
            'cpf': 'Não encontrado',
            'descricao': 'Não aplicável'
        }

def extract_judicial_cert_info(text):
    info = {}

    # Nome da certidão
    certidao_start = text.find("CERTIDÃO JUDICIAL")
    if certidao_start != -1:
        certidao_start += len("CERTIDÃO JUDICIAL")
        certidao_end = text.find("/", certidao_start)
        if certidao_end != -1:
            certidao_nome = text[certidao_start:certidao_end].strip()
            info['certidao'] = map_certidao_name(certidao_nome)
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
    
    # Descrição
    info['descricao'] = 'Não aplicável'
    
    return info

def extract_receita_cert_info(text):
    info = {}

    if "MINISTÉRIO DA FAZENDA" in text:
        info['certidao'] = "RECEITA"

    
    # Status da certidão
    if "não constam pendências em seu nome" in text:
        info['status'] = "NÃO CONSTAM DÉBITOS"
    elif "constam débitos" in text:
        info['status'] = "HÁ DÉBITOS"
    else:
        info['status'] = 'Não encontrado'
    
    
    # Nome da pessoa
    nome_start = text.find("Nome: ")
    if nome_start != -1:
        nome_start += len("Nome: ")
        nome_end = text.find("\nCPF:", nome_start)
        if nome_end != -1:
            info['nome'] = text[nome_start:nome_end].strip().upper()
        else:
            info['nome'] = text[nome_start:].strip().upper()
    else:
        info['nome'] = 'Não encontrado'
    
    # CPF da pessoa
    cpf_pattern = r"CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})"
    match = re.search(cpf_pattern, text)
    if match:
        info['cpf'] = match.group(1)
    else:
        info['cpf'] = 'Não encontrado'
    
    # Descrição de pendência
    descricao_start = text.find("é certificado que:")
    if descricao_start != -1:
        descricao_start += len("é certificado que:")
        descricao_end = text.find("Conforme disposto nos arts", descricao_start)
        if descricao_end != -1:
            info['descricao'] = text[descricao_start:descricao_end].strip()
        else:
            info['descricao'] = 'SEFAZ - SEM DÉBITOS'
    else:
        info['descricao'] = 'Não aplicável'
    
    
    return info

def extract_sefaz_cert_info(text):
    info = {}

    # Verifica se "MINISTÉRIO DA FAZENDA" está presente
    if "MINISTÉRIO DA FAZENDA" in text:
        return extract_receita_cert_info(text)
    
    # Nome da certidão
    if "CERTIDÃO NEGATIVA DE DÉBITOS" in text:
        info['certidao'] = "SEFAZ"
    elif "CERTIDÃO POSITIVA DE DÉBITOS COM EFEITO DE NEGATIVA" in text:
        info['certidao'] = "SEFAZ"
    else:
        info['certidao'] = 'Não encontrado'
    
    # Status da certidão
    if "Até esta data não constam débitos de tributos" in text:
        info['status'] = "NÃO CONSTAM DÉBITOS"
    elif "Pelos débitos acima responde solidariamente o adquirente" in text:
        info['status'] = "HÁ DÉBITOS"
    else:
        info['status'] = 'Não encontrado'
    
    # Nome da pessoa
    nome_start = text.find("NOME:")
    if nome_start != -1:
        nome_start += len("NOME:")
        endereco_start = text.find("ENDEREÇO:", nome_start)
        if endereco_start != -1:
            info['nome'] = text[nome_start:endereco_start].strip().upper()
        else:
            info['nome'] = text[nome_start:].strip().upper()
    else:
        info['nome'] = 'Não encontrado'
    
    # CPF da pessoa
    cpf_pattern = r"CPF:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})"
    match = re.search(cpf_pattern, text)
    if match:
        info['cpf'] = match.group(1)
    else:
        info['cpf'] = 'Não encontrado'
    
    # Descrição de pendência
    descricao_start = text.find("é certificado que:")
    if descricao_start != -1:
        descricao_start += len("é certificado que:")
        descricao_end = text.find("Conforme disposto nos arts", descricao_start)
        if descricao_end != -1:
            info['descricao'] = text[descricao_start:descricao_end].strip()
        else:
            info['descricao'] = 'SEFAZ - SEM DÉBITOS'
    else:
        info['descricao'] = 'Não aplicável'
    
    return info

def extract_trabalhista_cert_info(text):
    info = {}

    if "CERTIDÃO DE AÇÕES TRABALHISTAS EM TRAMITAÇÃO" in text:
        info['certidao'] = "TRABALHISTA"
    elif "CERTIDÃO POSITIVA DE DÉBITOS TRABALHISTAS" in text:
        info['certidao'] = "TRABALHISTA"
    else:
        info['certidao'] = 'Não encontrado'
    
    # Status da certidão
    if "NÃO CONSTA" in text:
        info['status'] = "NÃO CONSTAM AÇÔES TRABALHISTA"
    elif "constam débitos" in text:
        info['status'] = "HÁ DÉBITOS"
    else:
        info['status'] = 'Não encontrado'
    
    # Nome da pessoa
    nome_start = text.find("NOME:")
    if nome_start != -1:
        nome_start += len("NOME:")
        nome_end = text.find("\n", nome_start)
        if nome_end != -1:
            info['nome'] = text[nome_start:nome_end].strip().upper()
        else:
            info['nome'] = 'Não encontrado'
    else:
        info['nome'] = 'Não encontrado'
    
    # CPF da pessoa
    cpf_pattern = r"CPF/CNPJ:\s*(\d{3}\.\d{3}\.\d{3}-\d{2})"
    match = re.search(cpf_pattern, text)
    if match:
        info['cpf'] = match.group(1)
    else:
        info['cpf'] = 'Não encontrado'
    
    # Descrição de pendência
    info['descricao'] = 'Não aplicável'
    
    return info

def extract_falencia_cert_info(text):
    info = {}

    if "AÇÕES DE FALÊNCIAS E RECUPERAÇÕES JUDICIAIS" in text:
        info['certidao'] = "FALENCIA"
    elif "AÇÕES DE FALÊNCIAS E RECUPERAÇÕES JUDICIAIS" in text:
        info['certidao'] = "FALENCIA"
    else:
        info['certidao'] = 'Não encontrado'
    
    # Status da certidão
    if " NADA CONSTA" in text:
        info['status'] = "NADA CONSTA"
    elif "constam débitos" in text:
        info['status'] = "HÁ DÉBITOS"
    else:
        info['status'] = 'Não encontrado'
    
    # Nome da pessoa
    nome_start = text.find("de:\n")
    if nome_start != -1:
        nome_start += len("de:\n")
        nome_end = text.find("\n", nome_start)
        if nome_end != -1:
            info['nome'] = text[nome_start:nome_end].strip().upper()
        else:
            info['nome'] = 'Não encontrado'
    else:
        info['nome'] = 'Não encontrado'
    
    # CPF da pessoa
    cpf_pattern = r"\s*(\d{3}\.\d{3}\.\d{3}-\d{2})"
    match = re.search(cpf_pattern, text)
    if match:
        info['cpf'] = match.group(1)
    else:
        info['cpf'] = 'Não encontrado'
    
    # Descrição de pendência
    info['descricao'] = 'Não aplicável'
    
    return info



def extract_especial_cert_info(text):
    info = {}

    if "ESPECIAL - AÇÕES CÍVEIS E CRIMINAIS" in text:
        info['certidao'] = "ESPECIAL"
    elif "ESPECIAL - AÇÕES CÍVEIS E CRIMINAIS" in text:
        info['certidao'] = "ESPECIAL"
    else:
        info['certidao'] = 'Não encontrado'
    
    # Status da certidão
    if " NADA CONSTA" in text:
        info['status'] = "NADA CONSTA"
    elif "constam débitos" in text:
        info['status'] = "HÁ DÉBITOS"
    else:
        info['status'] = 'Não encontrado'
    
    # Nome da pessoa
    nome_start = text.find("de:\n")
    if nome_start != -1:
        nome_start += len("de:\n")
        nome_end = text.find("\n", nome_start)
        if nome_end != -1:
            info['nome'] = text[nome_start:nome_end].strip().upper()
        else:
            info['nome'] = 'Não encontrado'
    else:
        info['nome'] = 'Não encontrado'
    
    # CPF da pessoa
    cpf_pattern = r"\s*(\d{3}\.\d{3}\.\d{3}-\d{2})"
    match = re.search(cpf_pattern, text)
    if match:
        info['cpf'] = match.group(1)
    else:
        info['cpf'] = 'Não encontrado'
    
    # Descrição de pendência
    info['descricao'] = 'Não aplicável'
    
    return info


def map_certidao_name(certidao_nome):
    if "CÍVEL" in certidao_nome.upper():
        return "CERTIDÃO CÍVEL"
    elif "CRIMINAL" in certidao_nome.upper():
        return "CERTIDÃO CRIMINAL"
    elif "ELEITORAIS" in certidao_nome.upper():
        return "CERTIDÃO ELEITORAL"
    elif "FALÊNCIA" in certidao_nome.upper():
        return "CERTIDÃO FALÊNCIA"
    elif "TRABALHISTA" in certidao_nome.upper():
        return "CERTIDÃO TRABALHISTA"
    elif "SEFAZ" in certidao_nome.upper():
        return "CERTIDÃO SEFAZ"
    else:
        return certidao_nome.strip().upper()


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])
    app.run(debug=True, host='0.0.0.0', port=80 )
