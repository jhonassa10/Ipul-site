#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════╗
║       IPUL Brewster - Panel de Administración        ║
╚══════════════════════════════════════════════════════╝

Cómo usar:
  1. Abre una terminal en esta carpeta
  2. Ejecuta: python3 admin.py
  3. Abre tu navegador en: http://localhost:8080/admin
"""

import http.server
import json
import os
import shutil
import sys
import io
import uuid
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# ══════════════════════════════════════════════════════
#  REEMPLAZO DEL MÓDULO 'cgi' (eliminado en Python 3.13)
# ══════════════════════════════════════════════════════

class FileField:
    """Representa un archivo subido en un formulario multipart."""
    def __init__(self, filename, data, content_type=''):
        self.filename = filename
        self.file = io.BytesIO(data)
        self.content_type = content_type

class SimpleForm:
    """Contenedor simple para campos de formulario y archivos."""
    def __init__(self, fields, files):
        self._fields = fields   # dict str -> str
        self._files  = files    # dict str -> FileField

    def getvalue(self, name, default=''):
        return self._fields.get(name, default)

    def __contains__(self, name):
        return name in self._fields or name in self._files

    def __getitem__(self, name):
        if name in self._files:
            return self._files[name]
        return self._fields.get(name, '')

def parse_multipart(rfile, headers):
    """Parser de multipart/form-data que no depende del módulo 'cgi'."""
    content_type   = headers.get('Content-Type', '')
    content_length = int(headers.get('Content-Length', 0))
    body   = rfile.read(content_length)
    fields = {}
    files  = {}

    if 'multipart/form-data' not in content_type:
        return SimpleForm(fields, files)

    # Extraer boundary
    boundary = None
    for item in content_type.split(';'):
        item = item.strip()
        if item.startswith('boundary='):
            boundary = item[9:].strip('"')
            break

    if not boundary:
        return SimpleForm(fields, files)

    sep   = ('--' + boundary).encode()
    parts = body.split(sep)

    for part in parts[1:]:
        part = part.lstrip(b'\r\n')
        if part.startswith(b'--') or not part.strip():
            continue
        if part.endswith(b'\r\n'):
            part = part[:-2]
        if b'\r\n\r\n' not in part:
            continue

        headers_bytes, content = part.split(b'\r\n\r\n', 1)
        headers_str = headers_bytes.decode('utf-8', errors='replace')

        name     = None
        filename = None
        ctype    = 'text/plain'

        for line in headers_str.split('\r\n'):
            if 'Content-Disposition' in line:
                for param in line.split(';'):
                    param = param.strip()
                    if param.startswith('name='):
                        name = param[5:].strip('"')
                    elif param.startswith('filename='):
                        filename = param[9:].strip('"')
            elif 'Content-Type' in line and ':' in line:
                ctype = line.split(':', 1)[1].strip()

        if name is None:
            continue

        if filename:
            files[name] = FileField(filename, content, ctype)
        else:
            fields[name] = content.decode('utf-8', errors='replace')

    return SimpleForm(fields, files)

try:
    from bs4 import BeautifulSoup
except ImportError:
    os.system(f"{sys.executable} -m pip install beautifulsoup4 --break-system-packages -q")
    from bs4 import BeautifulSoup

SITE_DIR = Path(__file__).parent
PORT = 8080

# ══════════════════════════════════════════════════════
#  FUNCIONES DE LECTURA / ESCRITURA HTML
# ══════════════════════════════════════════════════════

def read_soup(filename):
    path = SITE_DIR / filename
    with open(path, 'r', encoding='utf-8') as f:
        return BeautifulSoup(f.read(), 'html.parser')

def write_soup(soup, filename):
    path = SITE_DIR / filename
    with open(path, 'w', encoding='utf-8') as f:
        f.write(str(soup))

# ── Galería ─────────────────────────────────────────

def is_hidden(element):
    """Verifica si un elemento HTML tiene display:none"""
    style = element.get('style', '')
    return 'display:none' in style.replace(' ', '')

def get_gallery_items():
    soup = read_soup('galeria.html')
    items = []
    grid = soup.find('div', class_='gallery-grid')
    if grid:
        for i, item in enumerate(grid.find_all('div', class_='gallery-item')):
            img = item.find('img')
            title_el = item.find('div', class_='gallery-title')
            cat_el   = item.find('div', class_='gallery-category')
            items.append({
                'index': i,
                'src':   img['src'] if img else '',
                'alt':   img.get('alt', '') if img else '',
                'title': title_el.text.strip() if title_el else '',
                'category_display': cat_el.text.strip() if cat_el else '',
                'category': (item.get('data-category') or '').strip(),
                'hidden': is_hidden(item),
            })
    return items

def toggle_gallery_item(img_src, hide):
    """Oculta o muestra una foto en galeria.html e index.html"""
    for fname in ['galeria.html', 'index.html']:
        fpath = SITE_DIR / fname
        if not fpath.exists():
            continue
        soup = read_soup(fname)
        grid = soup.find('div', class_='gallery-grid')
        if grid:
            for item in grid.find_all('div', class_='gallery-item'):
                img = item.find('img')
                if img and img.get('src') == img_src:
                    if hide:
                        item['style'] = 'display:none'
                    else:
                        item.attrs.pop('style', None)
            write_soup(soup, fname)

def replace_gallery_item(old_src, new_filename):
    """Reemplaza la imagen de una foto en galeria.html e index.html"""
    new_src = f'images/galeria/{new_filename}'
    for fname in ['galeria.html', 'index.html']:
        fpath = SITE_DIR / fname
        if not fpath.exists():
            continue
        soup = read_soup(fname)
        grid = soup.find('div', class_='gallery-grid')
        if grid:
            for item in grid.find_all('div', class_='gallery-item'):
                img = item.find('img')
                if img and img.get('src') == old_src:
                    img['src'] = new_src
                    img['alt'] = img.get('alt', '')
            write_soup(soup, fname)
    # Eliminar imagen antigua si está en la carpeta galeria
    old_path = SITE_DIR / old_src
    if old_path.exists() and 'galeria' in str(old_path):
        old_path.unlink()

def add_gallery_item(img_filename, title, category, category_display, alt=''):
    img_src = f'images/galeria/{img_filename}'
    new_html = f'''<div class="gallery-item" data-category="{category}">
                <img src="{img_src}" alt="{alt or title}">
                <div class="gallery-overlay">
                    <div class="gallery-title">{title}</div>
                    <div class="gallery-category">{category_display}</div>
                </div>
            </div>'''
    for fname in ['galeria.html', 'index.html']:
        fpath = SITE_DIR / fname
        if not fpath.exists():
            continue
        soup = read_soup(fname)
        grid = soup.find('div', class_='gallery-grid')
        if grid:
            grid.append(BeautifulSoup(new_html, 'html.parser'))
            write_soup(soup, fname)

def remove_gallery_item(img_src):
    for fname in ['galeria.html', 'index.html']:
        fpath = SITE_DIR / fname
        if not fpath.exists():
            continue
        soup = read_soup(fname)
        grid = soup.find('div', class_='gallery-grid')
        if grid:
            for item in grid.find_all('div', class_='gallery-item'):
                img = item.find('img')
                if img and img.get('src') == img_src:
                    item.decompose()
            write_soup(soup, fname)
    # Eliminar archivo físico
    full_path = SITE_DIR / img_src
    if full_path.exists() and 'galeria' in str(full_path):
        full_path.unlink()

# ── Eventos ─────────────────────────────────────────

def get_events():
    soup = read_soup('index.html')
    events = []
    grid = soup.find('div', class_='events-grid')
    if grid:
        for i, card in enumerate(grid.find_all('div', class_='event-card')):
            img    = card.find('img')
            tag    = card.find('div', class_='event-tag')
            title  = card.find('h3', class_='event-title')
            time_  = card.find('div', class_='event-time')
            desc   = card.find('p', class_='event-description')
            time_spans = time_.find_all('span') if time_ else []
            time_text = time_spans[1].get_text(strip=True) if len(time_spans) > 1 else ''
            events.append({
                'index':   i,
                'img_src': img['src'] if img else '',
                'tag':     tag.text.strip() if tag else '',
                'title':   title.text.strip() if title else '',
                'time':    time_text,
                'description': desc.get_text(strip=True) if desc else '',
                'hidden':  is_hidden(card),
            })
    return events

def toggle_event(event_index, hide):
    """Oculta o muestra un evento en index.html"""
    soup = read_soup('index.html')
    grid = soup.find('div', class_='events-grid')
    if grid:
        cards = grid.find_all('div', class_='event-card')
        if 0 <= event_index < len(cards):
            if hide:
                cards[event_index]['style'] = 'display:none'
            else:
                cards[event_index].attrs.pop('style', None)
            write_soup(soup, 'index.html')

def add_event(title, time_text, description, tag, img_src='images/community.jpg'):
    new_html = f'''<div class="event-card">
                <div class="event-image">
                    <img src="{img_src}" alt="{title}">
                    <div class="event-tag">{tag}</div>
                </div>
                <div class="event-content">
                    <h3 class="event-title">{title}</h3>
                    <div class="event-time">
                        <span>📅</span>
                        <span>{time_text}</span>
                    </div>
                    <p class="event-description">{description}</p>
                </div>
            </div>'''
    soup = read_soup('index.html')
    grid = soup.find('div', class_='events-grid')
    if grid:
        grid.append(BeautifulSoup(new_html, 'html.parser'))
        write_soup(soup, 'index.html')

def remove_event(event_index):
    soup = read_soup('index.html')
    grid = soup.find('div', class_='events-grid')
    if grid:
        cards = grid.find_all('div', class_='event-card')
        if 0 <= event_index < len(cards):
            cards[event_index].decompose()
            write_soup(soup, 'index.html')

def edit_event(event_index, title, time_text, description, tag):
    soup = read_soup('index.html')
    grid = soup.find('div', class_='events-grid')
    if grid:
        cards = grid.find_all('div', class_='event-card')
        if 0 <= event_index < len(cards):
            card = cards[event_index]
            t = card.find('h3', class_='event-title')
            if t: t.string = title
            tg = card.find('div', class_='event-tag')
            if tg: tg.string = tag
            spans = card.find('div', class_='event-time')
            if spans:
                sp = spans.find_all('span')
                if len(sp) > 1: sp[1].string = time_text
            d = card.find('p', class_='event-description')
            if d: d.string = description
            write_soup(soup, 'index.html')

# ── Directivas ──────────────────────────────────────

def get_directivas():
    soup = read_soup('directivas.html') if (SITE_DIR/'directivas.html').exists() else read_soup('index.html')
    items = []
    grids = soup.find_all('div', class_='directivas-grid')
    for grid in grids:
        for i, card in enumerate(grid.find_all('div', class_='directiva-card')):
            img  = card.find('img')
            h3   = card.find('h3')
            p    = card.find('p')
            items.append({
                'index': len(items),
                'img_src': img['src'] if img else '',
                'title':   h3.text.strip() if h3 else '',
                'info':    p.get_text('\n').strip() if p else '',
                'hidden':  is_hidden(card),
            })
    return items

def toggle_directiva(directiva_index, hide):
    """Oculta o muestra una directiva"""
    for fname in ['directivas.html', 'index.html']:
        fpath = SITE_DIR / fname
        if not fpath.exists():
            continue
        soup = read_soup(fname)
        all_cards = []
        for grid in soup.find_all('div', class_='directivas-grid'):
            all_cards.extend(grid.find_all('div', class_='directiva-card'))
        if 0 <= directiva_index < len(all_cards):
            if hide:
                all_cards[directiva_index]['style'] = 'display:none'
            else:
                all_cards[directiva_index].attrs.pop('style', None)
            write_soup(soup, fname)
            break

def edit_directiva(directiva_index, info_text):
    for fname in ['directivas.html', 'index.html']:
        fpath = SITE_DIR / fname
        if not fpath.exists():
            continue
        soup = read_soup(fname)
        all_cards = []
        for grid in soup.find_all('div', class_='directivas-grid'):
            all_cards.extend(grid.find_all('div', class_='directiva-card'))
        if 0 <= directiva_index < len(all_cards):
            card = all_cards[directiva_index]
            p = card.find('p')
            if p:
                p.clear()
                # Insert with line breaks
                lines = info_text.split('\n')
                for j, line in enumerate(lines):
                    p.append(line)
                    if j < len(lines) - 1:
                        p.append(soup.new_tag('br'))
            write_soup(soup, fname)
            break  # Only edit first found

# ══════════════════════════════════════════════════════
#  HTML DEL PANEL DE ADMINISTRACIÓN
# ══════════════════════════════════════════════════════

ADMIN_HTML = '''<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Panel Admin - IPUL Brewster</title>
<style>
:root {
  --primary: #1a4d8f;
  --primary-dark: #123a6e;
  --secondary: #d4af37;
  --danger: #e74c3c;
  --success: #27ae60;
  --light: #f8f9fa;
  --dark: #1a1a2e;
  --border: #dee2e6;
  --shadow: 0 4px 20px rgba(0,0,0,0.1);
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: 'Segoe UI', system-ui, sans-serif; background:#f0f4f8; color:#333; }

/* Header */
.admin-header {
  background: linear-gradient(135deg, var(--primary) 0%, #2563a8 100%);
  color: white; padding: 18px 40px;
  display: flex; align-items: center; gap: 20px;
  box-shadow: 0 2px 10px rgba(0,0,0,0.2);
  position: sticky; top: 0; z-index: 100;
}
.admin-header h1 { font-size: 22px; font-weight: 700; letter-spacing: 1px; }
.admin-header .badge {
  background: var(--secondary); color: #000;
  padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700;
}
.preview-link {
  margin-left: auto; color: white; text-decoration: none;
  background: rgba(255,255,255,0.2); padding: 8px 18px;
  border-radius: 8px; font-size: 14px; transition: background 0.2s;
}
.preview-link:hover { background: rgba(255,255,255,0.3); }

/* Tabs */
.tabs { display: flex; background: white; border-bottom: 2px solid var(--border); padding: 0 40px; }
.tab-btn {
  padding: 16px 28px; border: none; background: none;
  font-size: 15px; font-weight: 600; color: #666; cursor: pointer;
  border-bottom: 3px solid transparent; margin-bottom: -2px; transition: all 0.2s;
  display: flex; align-items: center; gap: 8px;
}
.tab-btn:hover { color: var(--primary); }
.tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); }

/* Content */
.content { max-width: 1100px; margin: 30px auto; padding: 0 20px; }
.tab-panel { display: none; }
.tab-panel.active { display: block; }

/* Section header */
.section-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 24px;
}
.section-header h2 { font-size: 24px; color: var(--dark); }

/* Cards grid */
.cards-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 20px; margin-bottom: 30px;
}

/* Photo card */
.photo-card {
  background: white; border-radius: 12px; overflow: hidden;
  box-shadow: var(--shadow); position: relative; transition: transform 0.2s;
}
.photo-card:hover { transform: translateY(-4px); }
.photo-card img { width:100%; height:180px; object-fit:cover; }
.photo-card .card-body { padding: 14px; }
.photo-card .card-title { font-weight: 700; font-size: 15px; margin-bottom: 4px; }
.photo-card .card-cat { font-size: 12px; color: var(--primary); text-transform: uppercase; letter-spacing: 1px; }
.photo-card .card-actions { display: flex; gap: 8px; margin-top: 12px; }

/* Event card */
.event-item {
  background: white; border-radius: 12px; padding: 20px;
  box-shadow: var(--shadow); display: flex; gap: 16px; align-items: flex-start;
  transition: transform 0.2s;
}
.event-item:hover { transform: translateY(-2px); }
.event-item img { width: 80px; height: 80px; object-fit: cover; border-radius: 10px; flex-shrink: 0; }
.event-info { flex: 1; }
.event-info .event-tag-badge {
  display: inline-block; background: var(--secondary); color: #000;
  padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: 700;
  text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;
}
.event-info h3 { font-size: 17px; margin-bottom: 6px; }
.event-info .event-time-text { color: #666; font-size: 13px; margin-bottom: 8px; }
.event-info p { font-size: 13px; color: #555; line-height: 1.5; }
.event-actions { display: flex; flex-direction: column; gap: 8px; flex-shrink: 0; }

/* Directiva card */
.directiva-item {
  background: white; border-radius: 12px; overflow: hidden;
  box-shadow: var(--shadow); transition: transform 0.2s;
}
.directiva-item:hover { transform: translateY(-4px); }
.directiva-item img { width:100%; height:160px; object-fit:cover; }
.directiva-body { padding: 16px; }
.directiva-body h3 { font-size: 17px; color: var(--primary); margin-bottom: 10px; }
.directiva-body p { font-size: 13px; color: #555; line-height: 1.7; }

/* Buttons */
.btn {
  padding: 8px 18px; border: none; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer; transition: all 0.2s;
  display: inline-flex; align-items: center; gap: 6px;
}
.btn-primary { background: var(--primary); color: white; }
.btn-primary:hover { background: var(--primary-dark); transform: translateY(-1px); }
.btn-danger { background: #fff0f0; color: var(--danger); border: 1px solid #fcc; }
.btn-danger:hover { background: var(--danger); color: white; }
.btn-success { background: var(--success); color: white; }
.btn-success:hover { background: #219150; }
.btn-secondary { background: #eee; color: #333; }
.btn-secondary:hover { background: #ddd; }
.btn-warning { background: #fff3cd; color: #856404; border: 1px solid #ffc107; }
.btn-warning:hover { background: #ffc107; color: #000; }
.btn-lg { padding: 12px 28px; font-size: 15px; border-radius: 10px; }

/* Modal */
.modal-overlay {
  display: none; position: fixed; top:0; left:0; width:100%; height:100%;
  background: rgba(0,0,0,0.6); z-index: 1000; align-items: center; justify-content: center;
}
.modal-overlay.active { display: flex; }
.modal {
  background: white; border-radius: 16px; padding: 30px;
  max-width: 540px; width: 90%; max-height: 90vh; overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0,0,0,0.3); animation: modalIn 0.2s ease;
}
@keyframes modalIn { from { transform: scale(0.9); opacity: 0; } to { transform: scale(1); opacity: 1; } }
.modal h2 { font-size: 22px; margin-bottom: 24px; color: var(--dark); border-bottom: 2px solid var(--border); padding-bottom: 14px; }
.modal-footer { display: flex; gap: 10px; justify-content: flex-end; margin-top: 24px; padding-top: 16px; border-top: 1px solid var(--border); }

/* Form */
.form-group { margin-bottom: 18px; }
.form-group label { display: block; font-weight: 600; font-size: 13px; margin-bottom: 6px; color: #444; }
.form-group input, .form-group select, .form-group textarea {
  width: 100%; padding: 10px 14px; border: 2px solid var(--border);
  border-radius: 8px; font-size: 14px; font-family: inherit;
  transition: border-color 0.2s; outline: none;
}
.form-group input:focus, .form-group select:focus, .form-group textarea:focus {
  border-color: var(--primary);
}
.form-group textarea { min-height: 90px; resize: vertical; }

/* File upload */
.upload-zone {
  border: 2px dashed var(--border); border-radius: 10px;
  padding: 30px; text-align: center; cursor: pointer;
  transition: all 0.2s; background: #fafafa;
}
.upload-zone:hover, .upload-zone.drag { border-color: var(--primary); background: #f0f4ff; }
.upload-zone .upload-icon { font-size: 40px; margin-bottom: 10px; }
.upload-zone p { color: #666; font-size: 14px; }
.upload-zone input[type=file] { display: none; }
.upload-preview { margin-top: 12px; }
.upload-preview img { max-height: 150px; border-radius: 8px; }

/* Toast */
.toast-container { position: fixed; bottom: 30px; right: 30px; z-index: 9999; display: flex; flex-direction: column; gap: 10px; }
.toast {
  background: #333; color: white; padding: 14px 20px; border-radius: 10px;
  font-size: 14px; font-weight: 500; box-shadow: 0 4px 20px rgba(0,0,0,0.3);
  animation: toastIn 0.3s ease; display: flex; align-items: center; gap: 10px;
  min-width: 260px;
}
.toast.success { background: var(--success); }
.toast.error { background: var(--danger); }
@keyframes toastIn { from { transform: translateX(100px); opacity: 0; } to { transform: translateX(0); opacity: 1; } }

/* Empty state */
.empty-state { text-align: center; padding: 60px 20px; color: #888; }
.empty-state .icon { font-size: 60px; margin-bottom: 16px; }
.empty-state p { font-size: 16px; }

/* Loading */
.loading { text-align: center; padding: 40px; color: #888; font-size: 18px; }

/* Events list */
.events-list { display: flex; flex-direction: column; gap: 16px; }

/* Stats bar */
.stats-bar {
  display: flex; gap: 16px; margin-bottom: 28px; flex-wrap: wrap;
}
.stat-card {
  background: white; border-radius: 12px; padding: 16px 24px;
  box-shadow: var(--shadow); flex: 1; min-width: 120px; text-align: center;
}
.stat-card .stat-num { font-size: 32px; font-weight: 800; color: var(--primary); }
.stat-card .stat-label { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; }

/* Oculto / Hidden */
.hidden-item { opacity: 0.45; }
.hidden-item img { filter: grayscale(60%); }
.hidden-badge {
  display: inline-flex; align-items: center; gap: 5px;
  background: #ffc107; color: #333; padding: 3px 10px;
  border-radius: 12px; font-size: 11px; font-weight: 700;
  margin-top: 6px; text-transform: uppercase; letter-spacing: 1px;
}
.btn-toggle-hide { background: #fff3cd; color: #856404; border: 1px solid #ffc107; }
.btn-toggle-hide:hover { background: #ffc107; color: #000; }
.btn-toggle-show { background: #d4edda; color: #155724; border: 1px solid #28a745; }
.btn-toggle-show:hover { background: #28a745; color: white; }
</style>
</head>
<body>

<!-- Header -->
<div class="admin-header">
  <span style="font-size:28px;">⛪</span>
  <div>
    <h1>IPUL Brewster</h1>
    <div style="font-size:12px;opacity:0.8;margin-top:2px;">Panel de Administración</div>
  </div>
  <span class="badge">ADMIN</span>
  <a href="/" target="_blank" class="preview-link">👁 Ver Sitio Web</a>
</div>

<!-- Tabs -->
<div class="tabs">
  <button class="tab-btn active" onclick="showTab('gallery')">📸 Galería</button>
  <button class="tab-btn" onclick="showTab('events')">📅 Eventos</button>
  <button class="tab-btn" onclick="showTab('directivas')">👥 Directivas</button>
</div>

<div class="content">

  <!-- ══ GALERÍA ══ -->
  <div id="tab-gallery" class="tab-panel active">
    <div class="section-header">
      <h2>🖼 Gestionar Galería</h2>
      <button class="btn btn-primary btn-lg" onclick="openModal('modal-add-photo')">
        ＋ Agregar Foto
      </button>
    </div>
    <div id="gallery-stats" class="stats-bar"></div>
    <div id="gallery-grid" class="cards-grid">
      <div class="loading">Cargando fotos...</div>
    </div>
  </div>

  <!-- ══ EVENTOS ══ -->
  <div id="tab-events" class="tab-panel">
    <div class="section-header">
      <h2>📋 Gestionar Eventos</h2>
      <button class="btn btn-primary btn-lg" onclick="openModal('modal-add-event')">
        ＋ Agregar Evento
      </button>
    </div>
    <div id="events-stats" class="stats-bar"></div>
    <div id="events-list" class="events-list">
      <div class="loading">Cargando eventos...</div>
    </div>
  </div>

  <!-- ══ DIRECTIVAS ══ -->
  <div id="tab-directivas" class="tab-panel">
    <div class="section-header">
      <h2>👥 Gestionar Directivas</h2>
      <div style="color:#666;font-size:14px;">Haz clic en "Editar" para modificar la información</div>
    </div>
    <div id="directivas-grid" class="cards-grid">
      <div class="loading">Cargando directivas...</div>
    </div>
  </div>

</div>

<!-- ════════════ MODALES ════════════ -->

<!-- Modal: Cambiar Foto -->
<div id="modal-replace-photo" class="modal-overlay" onclick="closeModalOutside(event, 'modal-replace-photo')">
  <div class="modal">
    <h2>🔄 Cambiar Foto</h2>
    <input type="hidden" id="replace-old-src" />
    <div class="form-group">
      <label>Foto actual</label>
      <img id="replace-current-img" src="" alt="" style="width:100%;height:160px;object-fit:cover;border-radius:10px;margin-bottom:8px;">
      <div style="font-weight:600;font-size:14px;" id="replace-current-title"></div>
    </div>
    <div class="form-group">
      <label>Nueva foto *</label>
      <div class="upload-zone" id="replace-upload-zone" onclick="document.getElementById('replace-photo-file').click()">
        <div class="upload-icon">🖼</div>
        <p>Haz clic para seleccionar la nueva foto<br><small>JPG, PNG, WEBP — reemplazará la foto actual</small></p>
        <input type="file" id="replace-photo-file" accept="image/*" onchange="previewReplacePhoto(this)">
        <div class="upload-preview" id="replace-upload-preview"></div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal('modal-replace-photo')">Cancelar</button>
      <button class="btn btn-success btn-lg" onclick="submitReplacePhoto()">✓ Reemplazar Foto</button>
    </div>
  </div>
</div>

<!-- Modal: Agregar Foto -->
<div id="modal-add-photo" class="modal-overlay" onclick="closeModalOutside(event, 'modal-add-photo')">
  <div class="modal">
    <h2>📸 Agregar Nueva Foto</h2>
    <div class="form-group">
      <label>Foto *</label>
      <div class="upload-zone" id="upload-zone" onclick="document.getElementById('photo-file').click()">
        <div class="upload-icon">🖼</div>
        <p>Haz clic para seleccionar una foto<br><small>JPG, PNG, WEBP - Máx. 10MB</small></p>
        <input type="file" id="photo-file" accept="image/*" onchange="previewPhoto(this)">
        <div class="upload-preview" id="upload-preview"></div>
      </div>
    </div>
    <div class="form-group">
      <label>Título de la foto *</label>
      <input type="text" id="photo-title" placeholder="Ej: Servicio Dominical" />
    </div>
    <div class="form-group">
      <label>Categoría *</label>
      <select id="photo-category">
        <option value="cultos">🎤 Cultos</option>
        <option value="eventos">✨ Eventos Especiales</option>
        <option value="comunidad">❤️ Comunidad</option>
        <option value="jovenes">🔥 Jóvenes</option>
        <option value="ninos">🌟 Niños</option>
      </select>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal('modal-add-photo')">Cancelar</button>
      <button class="btn btn-success btn-lg" onclick="submitAddPhoto()">✓ Guardar Foto</button>
    </div>
  </div>
</div>

<!-- Modal: Agregar Evento -->
<div id="modal-add-event" class="modal-overlay" onclick="closeModalOutside(event, 'modal-add-event')">
  <div class="modal">
    <h2>📅 Agregar Nuevo Evento</h2>
    <div class="form-group">
      <label>Título del evento *</label>
      <input type="text" id="event-title" placeholder="Ej: Noche de Adoración" />
    </div>
    <div class="form-group">
      <label>Categoría / Departamento *</label>
      <input type="text" id="event-tag" placeholder="Ej: Jóvenes, Iglesia, Damas..." />
    </div>
    <div class="form-group">
      <label>Fecha y Hora *</label>
      <input type="text" id="event-time" placeholder="Ej: Todos los Domingos 10:30 AM" />
    </div>
    <div class="form-group">
      <label>Descripción *</label>
      <textarea id="event-desc" placeholder="Descripción del evento..."></textarea>
    </div>
    <div class="form-group">
      <label>Foto del evento</label>
      <div class="upload-zone" id="event-upload-zone" onclick="document.getElementById('event-photo-file').click()">
        <div class="upload-icon">📷</div>
        <p>Clic para seleccionar foto (opcional)<br><small>Si no subes foto, se usará una imagen predeterminada</small></p>
        <input type="file" id="event-photo-file" accept="image/*" onchange="previewEventPhoto(this)">
        <div class="upload-preview" id="event-upload-preview"></div>
      </div>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal('modal-add-event')">Cancelar</button>
      <button class="btn btn-success btn-lg" onclick="submitAddEvent()">✓ Guardar Evento</button>
    </div>
  </div>
</div>

<!-- Modal: Editar Evento -->
<div id="modal-edit-event" class="modal-overlay" onclick="closeModalOutside(event, 'modal-edit-event')">
  <div class="modal">
    <h2>✏️ Editar Evento</h2>
    <input type="hidden" id="edit-event-index" />
    <div class="form-group">
      <label>Título del evento *</label>
      <input type="text" id="edit-event-title" />
    </div>
    <div class="form-group">
      <label>Categoría / Departamento *</label>
      <input type="text" id="edit-event-tag" />
    </div>
    <div class="form-group">
      <label>Fecha y Hora *</label>
      <input type="text" id="edit-event-time" />
    </div>
    <div class="form-group">
      <label>Descripción *</label>
      <textarea id="edit-event-desc"></textarea>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal('modal-edit-event')">Cancelar</button>
      <button class="btn btn-primary btn-lg" onclick="submitEditEvent()">✓ Actualizar</button>
    </div>
  </div>
</div>

<!-- Modal: Editar Directiva -->
<div id="modal-edit-directiva" class="modal-overlay" onclick="closeModalOutside(event, 'modal-edit-directiva')">
  <div class="modal">
    <h2>✏️ Editar Directiva</h2>
    <input type="hidden" id="edit-dir-index" />
    <div class="form-group">
      <label>Información (una persona por línea)</label>
      <textarea id="edit-dir-info" style="min-height:130px;" placeholder="Líder: Nombre\nSecretario: Nombre\nTesorero: Nombre"></textarea>
    </div>
    <div class="modal-footer">
      <button class="btn btn-secondary" onclick="closeModal('modal-edit-directiva')">Cancelar</button>
      <button class="btn btn-primary btn-lg" onclick="submitEditDirectiva()">✓ Actualizar</button>
    </div>
  </div>
</div>

<!-- Toast container -->
<div class="toast-container" id="toasts"></div>

<script>
// ══ State ══
let galleryItems = [];
let eventItems = [];
let directivaItems = [];

// ══ Tab switching ══
function showTab(name) {
  document.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + name).classList.add('active');
  event.currentTarget.classList.add('active');
  if (name === 'gallery' && galleryItems.length === 0) loadGallery();
  if (name === 'events' && eventItems.length === 0) loadEvents();
  if (name === 'directivas' && directivaItems.length === 0) loadDirectivas();
}

// ══ Load data ══
async function loadGallery() {
  const res = await fetch('/api/gallery');
  galleryItems = await res.json();
  renderGallery();
}

async function loadEvents() {
  const res = await fetch('/api/events');
  eventItems = await res.json();
  renderEvents();
}

async function loadDirectivas() {
  const res = await fetch('/api/directivas');
  directivaItems = await res.json();
  renderDirectivas();
}

// ══ Render functions ══
const CATEGORY_LABELS = {
  cultos: 'Cultos',
  eventos: 'Eventos Especiales',
  comunidad: 'Comunidad',
  jovenes: 'Jóvenes',
  ninos: 'Niños',
};
const CATEGORY_EMOJIS = { cultos:'🎤', eventos:'✨', comunidad:'❤️', jovenes:'🔥', ninos:'🌟' };

function renderGallery() {
  const grid = document.getElementById('gallery-grid');
  const stats = document.getElementById('gallery-stats');
  const total = galleryItems.length;
  const byCat = {};
  galleryItems.forEach(item => {
    byCat[item.category] = (byCat[item.category] || 0) + 1;
  });
  stats.innerHTML = `
    <div class="stat-card"><div class="stat-num">${total}</div><div class="stat-label">Total Fotos</div></div>
    ${Object.entries(byCat).map(([k,v]) => `<div class="stat-card"><div class="stat-num">${v}</div><div class="stat-label">${CATEGORY_EMOJIS[k]||''} ${CATEGORY_LABELS[k]||k}</div></div>`).join('')}
  `;
  if (galleryItems.length === 0) {
    grid.innerHTML = '<div class="empty-state"><div class="icon">🖼</div><p>No hay fotos aún. ¡Agrega la primera!</p></div>';
    return;
  }
  grid.innerHTML = galleryItems.map((item, i) => `
    <div class="photo-card ${item.hidden ? 'hidden-item' : ''}">
      <img src="${item.src}" alt="${item.alt}" onerror="this.src='https://via.placeholder.com/300x180?text=Foto'">
      <div class="card-body">
        <div class="card-title">${item.title || 'Sin título'}</div>
        <div class="card-cat">${CATEGORY_EMOJIS[item.category]||''} ${item.category_display || item.category}</div>
        ${item.hidden ? '<div class="hidden-badge">👁‍🗨 Oculto en el sitio</div>' : ''}
        <div class="card-actions" style="flex-wrap:wrap;">
          <button class="btn btn-primary" onclick="openReplacePhoto('${item.src}', '${item.title}')">🔄 Cambiar</button>
          ${item.hidden
            ? `<button class="btn btn-toggle-show" onclick="togglePhoto('${item.src}', false)">👁 Mostrar</button>`
            : `<button class="btn btn-toggle-hide" onclick="togglePhoto('${item.src}', true)">🙈 Ocultar</button>`
          }
          <button class="btn btn-danger" onclick="confirmRemovePhoto('${item.src}', '${item.title}')">🗑 Eliminar</button>
        </div>
      </div>
    </div>
  `).join('');
}

function renderEvents() {
  const list = document.getElementById('events-list');
  const stats = document.getElementById('events-stats');
  stats.innerHTML = `<div class="stat-card"><div class="stat-num">${eventItems.length}</div><div class="stat-label">Total Eventos</div></div>`;
  if (eventItems.length === 0) {
    list.innerHTML = '<div class="empty-state"><div class="icon">📅</div><p>No hay eventos aún. ¡Agrega el primero!</p></div>';
    return;
  }
  list.innerHTML = eventItems.map((ev, i) => `
    <div class="event-item ${ev.hidden ? 'hidden-item' : ''}">
      <img src="${ev.img_src}" alt="${ev.title}" onerror="this.src='https://via.placeholder.com/80?text=Foto'">
      <div class="event-info">
        <div class="event-tag-badge">${ev.tag}</div>
        <h3>${ev.title}</h3>
        <div class="event-time-text">📅 ${ev.time}</div>
        <p>${ev.description}</p>
        ${ev.hidden ? '<div class="hidden-badge" style="margin-top:8px;">👁‍🗨 Oculto en el sitio</div>' : ''}
      </div>
      <div class="event-actions">
        <button class="btn btn-warning" onclick="openEditEvent(${i})">✏️ Editar</button>
        ${ev.hidden
          ? `<button class="btn btn-toggle-show" onclick="toggleEvent(${i}, false)">👁 Mostrar</button>`
          : `<button class="btn btn-toggle-hide" onclick="toggleEvent(${i}, true)">🙈 Ocultar</button>`
        }
        <button class="btn btn-danger" onclick="confirmRemoveEvent(${i}, '${ev.title}')">🗑 Eliminar</button>
      </div>
    </div>
  `).join('');
}

function renderDirectivas() {
  const grid = document.getElementById('directivas-grid');
  if (directivaItems.length === 0) {
    grid.innerHTML = '<div class="empty-state"><div class="icon">👥</div><p>No se encontraron directivas.</p></div>';
    return;
  }
  grid.innerHTML = directivaItems.map((d, i) => `
    <div class="directiva-item ${d.hidden ? 'hidden-item' : ''}">
      <img src="${d.img_src}" alt="${d.title}" onerror="this.src='https://via.placeholder.com/300x160?text=Directiva'">
      <div class="directiva-body">
        <h3>${d.title}</h3>
        <p id="dir-text-${i}">${d.info.replace(/\\n/g,'<br>')}</p>
        ${d.hidden ? '<div class="hidden-badge">👁‍🗨 Oculto en el sitio</div>' : ''}
        <div style="margin-top:12px; display:flex; gap:8px; flex-wrap:wrap;">
          <button class="btn btn-warning" onclick="openEditDirectiva(${i})">✏️ Editar</button>
          ${d.hidden
            ? `<button class="btn btn-toggle-show" onclick="toggleDirectiva(${i}, false)">👁 Mostrar</button>`
            : `<button class="btn btn-toggle-hide" onclick="toggleDirectiva(${i}, true)">🙈 Ocultar</button>`
          }
        </div>
      </div>
    </div>
  `).join('');
}

// ══ Photo upload ══
function previewPhoto(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById('upload-preview').innerHTML = `<img src="${e.target.result}" style="max-height:150px;border-radius:8px;">`;
    document.getElementById('upload-zone').querySelector('p').style.display = 'none';
  };
  reader.readAsDataURL(file);
}

function previewEventPhoto(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById('event-upload-preview').innerHTML = `<img src="${e.target.result}" style="max-height:120px;border-radius:8px;">`;
  };
  reader.readAsDataURL(file);
}

async function submitAddPhoto() {
  const file = document.getElementById('photo-file').files[0];
  const title = document.getElementById('photo-title').value.trim();
  const catEl = document.getElementById('photo-category');
  const category = catEl.value;
  const category_display = catEl.options[catEl.selectedIndex].text.replace(/^[^ ]+ /, '');

  if (!file) { showToast('⚠️ Selecciona una foto', 'error'); return; }
  if (!title) { showToast('⚠️ Escribe el título de la foto', 'error'); return; }

  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title);
  formData.append('category', category);
  formData.append('category_display', category_display);

  const res = await fetch('/api/gallery/add', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.ok) {
    showToast('✅ Foto agregada correctamente');
    closeModal('modal-add-photo');
    resetPhotoForm();
    galleryItems = [];
    await loadGallery();
  } else {
    showToast('❌ Error: ' + data.error, 'error');
  }
}

function resetPhotoForm() {
  document.getElementById('photo-file').value = '';
  document.getElementById('photo-title').value = '';
  document.getElementById('upload-preview').innerHTML = '';
  document.getElementById('upload-zone').querySelector('p').style.display = '';
}

function openReplacePhoto(src, title) {
  document.getElementById('replace-old-src').value = src;
  document.getElementById('replace-current-img').src = src;
  document.getElementById('replace-current-title').textContent = title;
  document.getElementById('replace-upload-preview').innerHTML = '';
  document.getElementById('replace-photo-file').value = '';
  document.getElementById('replace-upload-zone').querySelector('p').style.display = '';
  openModal('modal-replace-photo');
}

function previewReplacePhoto(input) {
  const file = input.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = e => {
    document.getElementById('replace-upload-preview').innerHTML =
      `<img src="${e.target.result}" style="max-height:140px;border-radius:8px;margin-top:8px;">`;
    document.getElementById('replace-upload-zone').querySelector('p').style.display = 'none';
  };
  reader.readAsDataURL(file);
}

async function submitReplacePhoto() {
  const oldSrc = document.getElementById('replace-old-src').value;
  const file   = document.getElementById('replace-photo-file').files[0];
  if (!file) { showToast('⚠️ Selecciona una nueva foto', 'error'); return; }
  const formData = new FormData();
  formData.append('old_src', oldSrc);
  formData.append('file', file);
  const res  = await fetch('/api/gallery/replace', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.ok) {
    showToast('✅ Foto reemplazada correctamente');
    closeModal('modal-replace-photo');
    galleryItems = [];
    await loadGallery();
  } else {
    showToast('❌ Error: ' + data.error, 'error');
  }
}

async function togglePhoto(src, hide) {
  const formData = new FormData();
  formData.append('src', src);
  formData.append('hide', hide);
  const res = await fetch('/api/gallery/toggle', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.ok) {
    showToast(hide ? '🙈 Foto ocultada del sitio' : '👁 Foto visible en el sitio');
    galleryItems = [];
    await loadGallery();
  } else {
    showToast('❌ Error: ' + data.error, 'error');
  }
}

async function confirmRemovePhoto(src, title) {
  if (!confirm(`¿Eliminar la foto "${title}"?\n\nEsta acción no se puede deshacer.`)) return;
  const formData = new FormData();
  formData.append('src', src);
  const res = await fetch('/api/gallery/remove', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.ok) {
    showToast('🗑 Foto eliminada');
    galleryItems = [];
    await loadGallery();
  } else {
    showToast('❌ Error al eliminar', 'error');
  }
}

// ══ Events ══
async function submitAddEvent() {
  const title = document.getElementById('event-title').value.trim();
  const tag   = document.getElementById('event-tag').value.trim();
  const time  = document.getElementById('event-time').value.trim();
  const desc  = document.getElementById('event-desc').value.trim();

  if (!title || !tag || !time || !desc) {
    showToast('⚠️ Completa todos los campos obligatorios', 'error'); return;
  }

  const formData = new FormData();
  formData.append('title', title);
  formData.append('tag', tag);
  formData.append('time', time);
  formData.append('description', desc);

  const photoFile = document.getElementById('event-photo-file').files[0];
  if (photoFile) formData.append('photo', photoFile);

  const res = await fetch('/api/events/add', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.ok) {
    showToast('✅ Evento agregado correctamente');
    closeModal('modal-add-event');
    document.getElementById('event-title').value = '';
    document.getElementById('event-tag').value = '';
    document.getElementById('event-time').value = '';
    document.getElementById('event-desc').value = '';
    document.getElementById('event-upload-preview').innerHTML = '';
    eventItems = [];
    await loadEvents();
  } else {
    showToast('❌ Error: ' + data.error, 'error');
  }
}

function openEditEvent(index) {
  const ev = eventItems[index];
  document.getElementById('edit-event-index').value = index;
  document.getElementById('edit-event-title').value = ev.title;
  document.getElementById('edit-event-tag').value = ev.tag;
  document.getElementById('edit-event-time').value = ev.time;
  document.getElementById('edit-event-desc').value = ev.description;
  openModal('modal-edit-event');
}

async function submitEditEvent() {
  const index = document.getElementById('edit-event-index').value;
  const title = document.getElementById('edit-event-title').value.trim();
  const tag   = document.getElementById('edit-event-tag').value.trim();
  const time  = document.getElementById('edit-event-time').value.trim();
  const desc  = document.getElementById('edit-event-desc').value.trim();
  if (!title || !tag || !time || !desc) { showToast('⚠️ Completa todos los campos', 'error'); return; }
  const formData = new FormData();
  formData.append('index', index);
  formData.append('title', title);
  formData.append('tag', tag);
  formData.append('time', time);
  formData.append('description', desc);
  const res = await fetch('/api/events/edit', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.ok) {
    showToast('✅ Evento actualizado');
    closeModal('modal-edit-event');
    eventItems = [];
    await loadEvents();
  } else {
    showToast('❌ Error: ' + data.error, 'error');
  }
}

async function toggleEvent(index, hide) {
  const formData = new FormData();
  formData.append('index', index);
  formData.append('hide', hide);
  const res = await fetch('/api/events/toggle', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.ok) {
    showToast(hide ? '🙈 Evento ocultado del sitio' : '👁 Evento visible en el sitio');
    eventItems = [];
    await loadEvents();
  } else {
    showToast('❌ Error: ' + data.error, 'error');
  }
}

async function confirmRemoveEvent(index, title) {
  if (!confirm(`¿Eliminar el evento "${title}"?\n\nEsta acción no se puede deshacer.`)) return;
  const formData = new FormData();
  formData.append('index', index);
  const res = await fetch('/api/events/remove', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.ok) {
    showToast('🗑 Evento eliminado');
    eventItems = [];
    await loadEvents();
  } else {
    showToast('❌ Error al eliminar', 'error');
  }
}

// ══ Directivas ══
function openEditDirectiva(index) {
  const d = directivaItems[index];
  document.getElementById('edit-dir-index').value = index;
  document.getElementById('edit-dir-info').value = d.info;
  openModal('modal-edit-directiva');
}

async function submitEditDirectiva() {
  const index = document.getElementById('edit-dir-index').value;
  const info  = document.getElementById('edit-dir-info').value.trim();
  const formData = new FormData();
  formData.append('index', index);
  formData.append('info', info);
  const res = await fetch('/api/directivas/edit', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.ok) {
    showToast('✅ Directiva actualizada');
    closeModal('modal-edit-directiva');
    directivaItems = [];
    await loadDirectivas();
  } else {
    showToast('❌ Error: ' + data.error, 'error');
  }
}

async function toggleDirectiva(index, hide) {
  const formData = new FormData();
  formData.append('index', index);
  formData.append('hide', hide);
  const res = await fetch('/api/directivas/toggle', { method: 'POST', body: formData });
  const data = await res.json();
  if (data.ok) {
    showToast(hide ? '🙈 Directiva ocultada del sitio' : '👁 Directiva visible en el sitio');
    directivaItems = [];
    await loadDirectivas();
  } else {
    showToast('❌ Error: ' + data.error, 'error');
  }
}

// ══ Modal helpers ══
function openModal(id) { document.getElementById(id).classList.add('active'); }
function closeModal(id) { document.getElementById(id).classList.remove('active'); }
function closeModalOutside(e, id) { if (e.target.id === id) closeModal(id); }

// ══ Toast ══
function showToast(msg, type='success') {
  const c = document.getElementById('toasts');
  const t = document.createElement('div');
  t.className = 'toast ' + type;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ══ Init ══
loadGallery();
</script>
</body>
</html>
'''

# ══════════════════════════════════════════════════════
#  HTTP REQUEST HANDLER
# ══════════════════════════════════════════════════════

class AdminHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIR), **kwargs)

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip('/')

        if path == '/admin':
            self.send_html(ADMIN_HTML)
        elif path == '/api/gallery':
            self.send_json(get_gallery_items())
        elif path == '/api/events':
            self.send_json(get_events())
        elif path == '/api/directivas':
            self.send_json(get_directivas())
        else:
            super().do_GET()

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        ctype = self.headers.get('Content-Type', '')

        if 'multipart/form-data' in ctype:
            form = parse_multipart(self.rfile, self.headers)
        else:
            form = SimpleForm({}, {})

        try:
            if path == '/api/gallery/add':
                self.handle_gallery_add(form)
            elif path == '/api/gallery/remove':
                self.handle_gallery_remove(form)
            elif path == '/api/events/add':
                self.handle_events_add(form)
            elif path == '/api/events/remove':
                self.handle_events_remove(form)
            elif path == '/api/events/edit':
                self.handle_events_edit(form)
            elif path == '/api/directivas/edit':
                self.handle_directivas_edit(form)
            elif path == '/api/gallery/replace':
                self.handle_gallery_replace(form)
            elif path == '/api/gallery/toggle':
                self.handle_gallery_toggle(form)
            elif path == '/api/events/toggle':
                self.handle_events_toggle(form)
            elif path == '/api/directivas/toggle':
                self.handle_directivas_toggle(form)
            else:
                self.send_json({'ok': False, 'error': 'Endpoint no encontrado'}, 404)
        except Exception as e:
            self.send_json({'ok': False, 'error': str(e)}, 500)

    # ── Gallery handlers ──────────────────────────────

    def handle_gallery_add(self, form):
        file_item = form['file']
        title = form.getvalue('title', 'Sin título')
        category = form.getvalue('category', 'comunidad')
        category_display = form.getvalue('category_display', category.capitalize())

        # Get a safe filename
        orig_name = file_item.filename or 'photo.jpg'
        ext = Path(orig_name).suffix.lower() or '.jpg'
        safe_name = uuid.uuid4().hex[:10] + ext

        dest = SITE_DIR / 'images' / 'galeria' / safe_name
        dest.parent.mkdir(parents=True, exist_ok=True)

        with open(dest, 'wb') as f:
            f.write(file_item.file.read())

        add_gallery_item(safe_name, title, category, category_display)
        self.send_json({'ok': True, 'filename': safe_name})

    def handle_gallery_remove(self, form):
        src = form.getvalue('src', '')
        if not src:
            self.send_json({'ok': False, 'error': 'src requerido'}); return
        remove_gallery_item(src)
        self.send_json({'ok': True})

    # ── Events handlers ───────────────────────────────

    def handle_events_add(self, form):
        title  = form.getvalue('title', '')
        tag    = form.getvalue('tag', '')
        time   = form.getvalue('time', '')
        desc   = form.getvalue('description', '')
        img_src = 'images/community.jpg'

        # Handle optional photo upload
        if 'photo' in form and form['photo'].filename:
            file_item = form['photo']
            ext = Path(file_item.filename).suffix.lower() or '.jpg'
            safe_name = uuid.uuid4().hex[:10] + ext
            dest = SITE_DIR / 'images' / safe_name
            with open(dest, 'wb') as f:
                f.write(file_item.file.read())
            img_src = f'images/{safe_name}'

        add_event(title, time, desc, tag, img_src)
        self.send_json({'ok': True})

    def handle_events_remove(self, form):
        idx = int(form.getvalue('index', -1))
        if idx < 0:
            self.send_json({'ok': False, 'error': 'index inválido'}); return
        remove_event(idx)
        self.send_json({'ok': True})

    def handle_events_edit(self, form):
        idx   = int(form.getvalue('index', -1))
        title = form.getvalue('title', '')
        tag   = form.getvalue('tag', '')
        time  = form.getvalue('time', '')
        desc  = form.getvalue('description', '')
        if idx < 0:
            self.send_json({'ok': False, 'error': 'index inválido'}); return
        edit_event(idx, title, time, desc, tag)
        self.send_json({'ok': True})

    # ── Directivas handlers ───────────────────────────

    def handle_directivas_edit(self, form):
        idx  = int(form.getvalue('index', -1))
        info = form.getvalue('info', '')
        if idx < 0:
            self.send_json({'ok': False, 'error': 'index inválido'}); return
        edit_directiva(idx, info)
        self.send_json({'ok': True})

    # ── Toggle (ocultar/mostrar) handlers ─────────────

    def handle_gallery_replace(self, form):
        old_src   = form.getvalue('old_src', '')
        file_item = form['file'] if 'file' in form else None
        if not old_src or not file_item or not file_item.filename:
            self.send_json({'ok': False, 'error': 'Datos incompletos'}); return
        ext       = Path(file_item.filename).suffix.lower() or '.jpg'
        safe_name = uuid.uuid4().hex[:10] + ext
        dest      = SITE_DIR / 'images' / 'galeria' / safe_name
        dest.parent.mkdir(parents=True, exist_ok=True)
        with open(dest, 'wb') as f:
            f.write(file_item.file.read())
        replace_gallery_item(old_src, safe_name)
        self.send_json({'ok': True, 'new_src': f'images/galeria/{safe_name}'})

    def handle_gallery_toggle(self, form):
        src  = form.getvalue('src', '')
        hide = form.getvalue('hide', 'true') == 'true'
        if not src:
            self.send_json({'ok': False, 'error': 'src requerido'}); return
        toggle_gallery_item(src, hide)
        self.send_json({'ok': True})

    def handle_events_toggle(self, form):
        idx  = int(form.getvalue('index', -1))
        hide = form.getvalue('hide', 'true') == 'true'
        if idx < 0:
            self.send_json({'ok': False, 'error': 'index inválido'}); return
        toggle_event(idx, hide)
        self.send_json({'ok': True})

    def handle_directivas_toggle(self, form):
        idx  = int(form.getvalue('index', -1))
        hide = form.getvalue('hide', 'true') == 'true'
        if idx < 0:
            self.send_json({'ok': False, 'error': 'index inválido'}); return
        toggle_directiva(idx, hide)
        self.send_json({'ok': True})

    # ── Helpers ───────────────────────────────────────

    def send_html(self, html):
        data = html.encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def send_json(self, obj, code=200):
        data = json.dumps(obj, ensure_ascii=False, indent=2).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, format, *args):
        # Clean log output
        if '/api/' in (args[0] if args else ''):
            print(f"  → {args[0]} {args[1]}")

# ══════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════

if __name__ == '__main__':
    import socketserver

    print()
    print("╔══════════════════════════════════════════════════════╗")
    print("║       IPUL Brewster - Panel de Administración        ║")
    print("╠══════════════════════════════════════════════════════╣")
    print(f"║  Servidor iniciado en: http://localhost:{PORT}/admin  ║")
    print("║  Presiona Ctrl+C para detener el servidor            ║")
    print("╚══════════════════════════════════════════════════════╝")
    print()

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), AdminHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n  ✓ Servidor detenido. ¡Hasta pronto!")
