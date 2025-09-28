import os
import re
import argparse
from pathlib import Path
from deep_translator import GoogleTranslator
import time
import sys
from datetime import datetime, timedelta

class CodeTranslator:
    def __init__(self):
        self.translator = GoogleTranslator(source='zh-CN', target='en')
        self.processed_files = 0
        self.translated_comments = 0
        self.translated_strings = 0
        self.translated_markdown = 0
        self.translated_identifiers = 0
        self.total_files = 0
        self.start_time = None
        self.current_file = ""
        
        # Padrões regex para detectar comentários
        self.comment_patterns = {
            '.py': {
                'single_line': r'#.*',
                'multi_line': r"'''[\s\S]*?'''|\"\"\"[\s\S]*?\"\"\""
            },
            '.cpp': {
                'single_line': r'//.*',
                'multi_line': r'/\*[\s\S]*?\*/'
            },
            '.c': {
                'single_line': r'//.*',
                'multi_line': r'/\*[\s\S]*?\*/'
            },
            '.java': {
                'single_line': r'//.*',
                'multi_line': r'/\*[\s\S]*?\*/'
            },
            '.js': {
                'single_line': r'//.*',
                'multi_line': r'/\*[\s\S]*?\*/'
            },
            '.ts': {
                'single_line': r'//.*',
                'multi_line': r'/\*[\s\S]*?\*/'
            },
            '.html': {
                'single_line': r'<!--.*?-->',
                'multi_line': r'<!--[\s\S]*?-->'
            },
            '.css': {
                'single_line': r'//.*',
                'multi_line': r'/\*[\s\S]*?\*/'
            },
            '.php': {
                'single_line': r'#.*|//.*',
                'multi_line': r'/\*[\s\S]*?\*/'
            },
            '.h': {
                'single_line': r'//.*',
                'multi_line': r'/\*[\s\S]*?\*/'
            },
            '.ino': {
                'single_line': r'//.*',
                'multi_line': r'/\*[\s\S]*?\*/'
            },
            '.md': {
                'single_line': r'',
                'multi_line': r''
            }
        }

    def count_total_files(self, root_dir):
        """Conta o total de arquivos que serão processados"""
        supported_extensions = [ext for ext in self.comment_patterns.keys()]
        total = 0
        
        for root, dirs, files in os.walk(root_dir):
            # Ignora diretórios de sistema comuns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
            
            for file in files:
                file_extension = Path(file).suffix.lower()
                if file_extension in supported_extensions:
                    total += 1
        
        return total
    
    def format_time(self, seconds):
        """Formata segundos para formato legível"""
        if seconds < 60:
            return f"{seconds:.1f}s"
        elif seconds < 3600:
            minutes = seconds // 60
            seconds = seconds % 60
            return f"{int(minutes)}min {int(seconds)}s"
        else:
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            return f"{int(hours)}h {int(minutes)}min"
    
    def format_eta(self, elapsed, processed, total):
        """Calcula e formata o tempo estimado para conclusão"""
        if processed == 0:
            return "Calculando..."
        
        time_per_file = elapsed / processed
        remaining_files = total - processed
        eta_seconds = time_per_file * remaining_files
        
        if eta_seconds > 0:
            eta_time = datetime.now() + timedelta(seconds=eta_seconds)
            return f"{self.format_time(eta_seconds)} ({eta_time.strftime('%H:%M:%S')})"
        else:
            return "Calculando..."
    
    def update_progress(self, file_path, is_processed=False, has_chinese=False):
        """Atualiza a barra de progresso"""
        elapsed = time.time() - self.start_time
        progress = (self.processed_files / self.total_files) * 100 if self.total_files > 0 else 0
        
        # Limpa a linha atual
        sys.stdout.write('\r' + ' ' * 100 + '\r')
        
        # Barra de progresso
        bar_length = 30
        filled_length = int(bar_length * progress / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        
        # Informações principais
        sys.stdout.write(f'[{bar}] {progress:.1f}% ')
        sys.stdout.write(f'({self.processed_files}/{self.total_files}) ')
        
        # Tempo decorrido e ETA
        sys.stdout.write(f'⏱️ {self.format_time(elapsed)} ')
        sys.stdout.write(f'📅 ETA: {self.format_eta(elapsed, self.processed_files, self.total_files)} ')
        
        # Estatísticas de tradução
        sys.stdout.write(f'📝 {self.translated_comments}c {self.translated_strings}s {self.translated_identifiers}i {self.translated_markdown}md')
        
        # Arquivo atual (truncado se muito longo)
        current_file_display = os.path.basename(file_path)
        if len(current_file_display) > 30:
            current_file_display = "..." + current_file_display[-27:]
        
        sys.stdout.write(f' | 📄 {current_file_display}')
        
        # Status do arquivo atual
        if is_processed:
            if has_chinese:
                sys.stdout.write(' ✓')
            else:
                sys.stdout.write(' ∅')
        
        sys.stdout.flush()
    
    def contains_chinese(self, text):
        """Verifica se o texto contém caracteres chineses"""
        return bool(re.search(r'[\u4e00-\u9fff]', text))
    
    def extract_comments(self, content, file_extension):
        """Extrai comentários do conteúdo do arquivo"""
        if file_extension not in self.comment_patterns:
            return []
        
        comments = []
        patterns = self.comment_patterns[file_extension]
        
        # Comentários de uma linha
        single_line_matches = re.finditer(patterns['single_line'], content)
        for match in single_line_matches:
            comment_text = match.group(0)
            if self.contains_chinese(comment_text):
                comments.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': comment_text,
                    'type': 'comment'
                })
        
        # Comentários multi-linha
        multi_line_matches = re.finditer(patterns['multi_line'], content, re.DOTALL)
        for match in multi_line_matches:
            comment_text = match.group(0)
            if self.contains_chinese(comment_text):
                comments.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': comment_text,
                    'type': 'comment'
                })
        
        return sorted(comments, key=lambda x: x['start'], reverse=True)
    
    def extract_strings(self, content, file_extension):
        """Extrai strings de texto do código que contêm chinês - VERSÃO CORRIGIDA"""
        strings = []
        
        # Padrão único para capturar TODAS as strings entre aspas
        string_pattern = r'"(?:\\.|[^"\\])*"'
        
        all_strings = re.finditer(string_pattern, content)
        for match in all_strings:
            full_string = match.group(0)
            string_content = full_string[1:-1]  # Remove as aspas
            
            if self.contains_chinese(string_content):
                strings.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': full_string,
                    'content': string_content,
                    'type': 'string'
                })
        
        return sorted(strings, key=lambda x: x['start'], reverse=True)

    def extract_identifiers(self, content, file_extension):
        """Extrai identificadores (variáveis, funções) com nomes em chinês - VERSÃO CORRIGIDA"""
        identifiers = []
        
        # Só processa para linguagens C-like
        if file_extension not in ['.c', '.cpp', '.h', '.java', '.js', '.ts']:
            return identifiers
        
        # CORREÇÃO: Padrão mais abrangente para capturar variáveis
        # Captura: int 计数器, char *消息, float 变量名, etc.
        variable_pattern = r'\b(int|char|float|double|void|bool|string|long|short)\s+(\*?\s*[\u4e00-\u9fff][\u4e00-\u9fff_a-zA-Z0-9]*)\b'
        
        matches = re.finditer(variable_pattern, content)
        for match in matches:
            identifier_name = match.group(2).strip()
            if self.contains_chinese(identifier_name):
                identifiers.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': match.group(0),
                    'name': identifier_name,
                    'full_match': match.group(0),
                    'type': 'variable_declaration'
                })
        
        # CORREÇÃO: Padrão para uso de variáveis (em expressões, loops, etc.)
        variable_usage_pattern = r'\b([\u4e00-\u9fff][\u4e00-\u9fff_a-zA-Z0-9]*)\b'
        usage_matches = re.finditer(variable_usage_pattern, content)
        
        for match in usage_matches:
            var_name = match.group(1)
            
            # Verifica se é realmente uma variável (não parte de string ou comentário)
            context_start = max(0, match.start() - 2)
            context_end = min(len(content), match.end() + 2)
            context = content[context_start:context_end]
            
            # Pula se estiver dentro de string ou comentário
            if '"' in context or "'" in context or '//' in context or '/*' in context:
                continue
            
            if self.contains_chinese(var_name):
                identifiers.append({
                    'start': match.start(),
                    'end': match.end(),
                    'text': var_name,
                    'name': var_name,
                    'full_match': var_name,
                    'type': 'variable_usage'
                })
        
        return sorted(identifiers, key=lambda x: x['start'], reverse=True)

    def translate_identifier_name(self, chinese_name):
        """Traduz um nome de identificador do chinês para inglês - VERSÃO CORRIGIDA"""
        try:
            # Remove asteriscos e espaços para traduzir apenas o nome
            clean_name = chinese_name.replace('*', '').strip()
            
            # Traduz o nome
            translated = self.translator.translate(clean_name)
            
            # Converte para snake_case
            cleaned = re.sub(r'[^\w\s]', '', translated)
            snake_case = re.sub(r'\s+', '_', cleaned.strip()).lower()
            
            # Garante que não começa com número
            if snake_case and snake_case[0].isdigit():
                snake_case = 'var_' + snake_case
            
            # CORREÇÃO: Restaura asteriscos se existiam no original
            if '*' in chinese_name:
                snake_case = '*' + snake_case
            
            return snake_case
            
        except Exception as e:
            print(f"\n❌ Erro traduzindo identificador '{chinese_name}': {e}")
            return chinese_name

    def translate_comment(self, comment_text):
        """Traduz comentários preservando a formatação"""
        if comment_text.startswith('#'):
            content = comment_text[1:].lstrip()
            if self.contains_chinese(content):
                translated = self.translator.translate(content)
                return f"# {translated}"
        
        elif comment_text.startswith('//'):
            content = comment_text[2:].lstrip()
            if self.contains_chinese(content):
                translated = self.translator.translate(content)
                return f"// {translated}"
        
        elif comment_text.startswith('/*') and comment_text.endswith('*/'):
            content = comment_text[2:-2].strip()
            if self.contains_chinese(content):
                translated = self.translator.translate(content)
                if '\n' in comment_text:
                    lines = content.split('\n')
                    translated_lines = []
                    for line in lines:
                        if self.contains_chinese(line.strip()):
                            translated_lines.append(self.translator.translate(line.strip()))
                        else:
                            translated_lines.append(line)
                    return f"/*\n" + "\n".join(translated_lines) + "\n*/"
                else:
                    return f"/* {translated} */"
        
        elif comment_text.startswith('<!--') and comment_text.endswith('-->'):
            content = comment_text[4:-3].strip()
            if self.contains_chinese(content):
                translated = self.translator.translate(content)
                return f"<!-- {translated} -->"
        
        return comment_text

    def translate_string(self, string_data):
        """Traduz strings preservando a estrutura original"""
        string_content = string_data['content']
        
        if not self.contains_chinese(string_content):
            return string_data['text']
        
        try:
            translated_content = self.translator.translate(string_content)
            return f'"{translated_content}"'
            
        except Exception as e:
            print(f"\n❌ Erro traduzindo string: {e}")
            return string_data['text']

    def translate_identifier(self, identifier_data):
        """Traduz um identificador (variável, função) - VERSÃO CORRIGIDA"""
        chinese_name = identifier_data['name']
        
        if not self.contains_chinese(chinese_name):
            return identifier_data['text']
        
        try:
            translated_name = self.translate_identifier_name(chinese_name)
            
            # CORREÇÃO: Para declarações completas, substitui apenas o nome mantendo o tipo
            if identifier_data['type'] == 'variable_declaration':
                original_text = identifier_data['full_match']
                # Substitui apenas o nome da variável, mantendo tipo e asteriscos
                parts = original_text.split()
                if len(parts) >= 2:
                    # Reconstroi mantendo tipo e substituindo nome
                    parts[-1] = translated_name
                    return ' '.join(parts)
                else:
                    return original_text.replace(chinese_name, translated_name)
            
            # CORREÇÃO: Para uso de variáveis, substitui diretamente
            elif identifier_data['type'] == 'variable_usage':
                return translated_name
            
        except Exception as e:
            print(f"\n❌ Erro traduzindo identificador: {e}")
            return identifier_data['text']

    def translate_text(self, text, text_type, context=None):
        """Função de tradução unificada"""
        try:
            if text_type == 'comment':
                return self.translate_comment(text)
            elif text_type in ['string', 'esp_log', 'serial_print', 'printf_like', 'log_functions']:
                if context and 'content' in context:
                    return self.translate_string(context)
                return text
            elif text_type in ['variable_declaration', 'variable_usage']:
                if context and 'name' in context:
                    return self.translate_identifier(context)
                return text
            else:
                return text
        except Exception as e:
            print(f"\n❌ Erro na tradução: {e}")
            return text

    def process_markdown_file(self, file_path, content):
        """Processa arquivos Markdown especificamente"""
        lines = content.split('\n')
        translated_count = 0
        
        for i, line in enumerate(lines):
            if self.contains_chinese(line):
                try:
                    translated = self.translator.translate(line)
                    lines[i] = translated
                    translated_count += 1
                    self.translated_markdown += 1
                except Exception as e:
                    print(f"\n❌ Erro traduzindo linha Markdown: {e}")
        
        return '\n'.join(lines), translated_count

    def process_file(self, file_path):
        """Processa um único arquivo com suporte a identificadores - VERSÃO CORRIGIDA"""
        try:
            self.current_file = file_path
            self.update_progress(file_path)
            
            with open(file_path, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            file_extension = Path(file_path).suffix.lower()
            
            # Processa Markdown
            if file_extension == '.md':
                new_content, translated_count = self.process_markdown_file(file_path, original_content)
                if translated_count > 0:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    self.processed_files += 1
                    self.update_progress(file_path, is_processed=True, has_chinese=True)
                    return True
                else:
                    self.update_progress(file_path, is_processed=True, has_chinese=False)
                    return False
            
            # Processa código normalmente
            content = original_content
            changes_made = False
            
            # CORREÇÃO: Processa identificadores PRIMEIRO para evitar conflitos
            identifiers = self.extract_identifiers(content, file_extension)
            
            # Aplica tradução de identificadores primeiro
            if identifiers:
                content_after_identifiers = content
                for identifier in identifiers:
                    original_text = identifier['text']
                    translated = self.translate_text(original_text, identifier['type'], identifier)
                    
                    if translated != original_text:
                        content_after_identifiers = content_after_identifiers[:identifier['start']] + translated + content_after_identifiers[identifier['end']:]
                        self.translated_identifiers += 1
                        changes_made = True
                
                content = content_after_identifiers
            
            # Depois processa comentários e strings
            comments = self.extract_comments(content, file_extension)
            strings = self.extract_strings(content, file_extension)
            
            # Combina comentários e strings
            elements_to_translate = []
            
            for comment in comments:
                elements_to_translate.append({
                    'start': comment['start'],
                    'end': comment['end'],
                    'text': comment['text'],
                    'type': 'comment',
                    'context': None
                })
            
            for string in strings:
                elements_to_translate.append({
                    'start': string['start'],
                    'end': string['end'],
                    'text': string['text'],
                    'type': string['type'],
                    'context': string
                })
            
            elements_to_translate = sorted(elements_to_translate, key=lambda x: x['start'], reverse=True)
            
            # Aplica tradução de comentários e strings
            new_content = content
            for element in elements_to_translate:
                original_text = element['text']
                translated = self.translate_text(original_text, element['type'], element.get('context', {}))
                
                if translated != original_text:
                    new_content = new_content[:element['start']] + translated + new_content[element['end']:]
                    
                    if element['type'] == 'comment':
                        self.translated_comments += 1
                    else:
                        self.translated_strings += 1
                    
                    changes_made = True
            
            # Salva apenas se houver alterações
            if changes_made and new_content != original_content:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(new_content)
                self.processed_files += 1
                self.update_progress(file_path, is_processed=True, has_chinese=True)
                return True
            else:
                self.update_progress(file_path, is_processed=True, has_chinese=False)
                return False
            
        except Exception as e:
            print(f"\n❌ Erro crítico ao processar {file_path}: {e}")
            import traceback
            traceback.print_exc()
            self.update_progress(file_path, is_processed=True, has_chinese=False)
            return False

    def process_directory(self, root_dir):
        """Processa todos os arquivos fonte no diretório"""
        supported_extensions = [ext for ext in self.comment_patterns.keys()]
        
        print(f"🔍 Analisando diretório: {root_dir}")
        print(f"📁 Extensões suportadas: {', '.join(supported_extensions)}")
        print(f"📄 Incluindo agora: Arquivos Markdown (.md)")
        
        # Conta total de arquivos
        print("📊 Contando arquivos...")
        self.total_files = self.count_total_files(root_dir)
        
        if self.total_files == 0:
            print("❌ Nenhum arquivo encontrado para processar!")
            return
        
        print(f"📈 Total de arquivos a processar: {self.total_files}")
        print("⚠️  AVISO: Processando cada arquivo UMA ÚNICA VEZ para evitar duplicações")
        print("-" * 80)
        
        self.start_time = time.time()
        
        for root, dirs, files in os.walk(root_dir):
            # Ignora diretórios de sistema comuns
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['node_modules', 'venv', '__pycache__']]
            
            for file in files:
                file_path = os.path.join(root, file)
                file_extension = Path(file).suffix.lower()
                
                if file_extension in supported_extensions:
                    self.process_file(file_path)
                    time.sleep(0.3)
        
        # Linha final de conclusão
        print("\n" + "=" * 80)
        total_time = time.time() - self.start_time
        print(f"✅ Processamento concluído!")
        print(f"📊 Estatísticas finais:")
        print(f"   • Arquivos processados: {self.processed_files}/{self.total_files}")
        print(f"   • Comentários traduzidos: {self.translated_comments}")
        print(f"   • Strings traduzidas: {self.translated_strings}")
        print(f"   • Identificadores traduzidos: {self.translated_identifiers}")
        print(f"   • Conteúdo Markdown traduzido: {self.translated_markdown}")
        if total_time > 0:
            print(f"   • Tempo total: {self.format_time(total_time)}")
            print(f"   • Velocidade: {self.processed_files/total_time:.1f} arquivos/segundo")

def main():
    parser = argparse.ArgumentParser(description='Traduz comentários, strings e conteúdo Markdown em chinês para inglês')
    parser.add_argument('directory', help='Diretório raiz para processar')
    parser.add_argument('--backup', action='store_true', help='Cria backup dos arquivos originais')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.directory):
        print(f"❌ Erro: Diretório {args.directory} não encontrado!")
        return
    
    # Cria backup se solicitado
    if args.backup:
        import shutil
        backup_dir = f"{args.directory}_backup"
        if not os.path.exists(backup_dir):
            print(f"💾 Criando backup em: {backup_dir}")
            shutil.copytree(args.directory, backup_dir)
            print(f"✅ Backup criado com sucesso!")
        else:
            print(f"💾 Backup já existe em: {backup_dir}")
    
    print("🚀 Iniciando tradução...")
    translator = CodeTranslator()
    translator.process_directory(args.directory)

if __name__ == "__main__":
    main()
