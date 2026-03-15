#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Utility per creare il logo Katana per la GUI
"""

from PIL import Image, ImageDraw
import base64
import io

def create_katana_logo_svg():
    """Crea un logo SVG stilizzato di una katana"""
    svg_content = '''
<svg width="120" height="40" viewBox="0 0 120 40" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="blade" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#E8E8E8;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#FFFFFF;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#C0C0C0;stop-opacity:1" />
    </linearGradient>
    <linearGradient id="handle" x1="0%" y1="0%" x2="100%" y2="0%">
      <stop offset="0%" style="stop-color:#8B4513;stop-opacity:1" />
      <stop offset="50%" style="stop-color:#A0522D;stop-opacity:1" />
      <stop offset="100%" style="stop-color:#654321;stop-opacity:1" />
    </linearGradient>
  </defs>
  
  <!-- Lama della katana -->
  <path d="M15 18 L95 18 L100 20 L95 22 L15 22 Z" fill="url(#blade)" stroke="#999" stroke-width="0.5"/>
  
  <!-- Punta della lama -->
  <path d="M95 18 L105 20 L95 22 Z" fill="url(#blade)" stroke="#999" stroke-width="0.5"/>
  
  <!-- Guardia (tsuba) -->
  <rect x="12" y="16" width="6" height="8" fill="#2C2C2C" stroke="#000" stroke-width="0.5" rx="1"/>
  
  <!-- Manico (tsuka) -->
  <rect x="2" y="17" width="12" height="6" fill="url(#handle)" stroke="#654321" stroke-width="0.5" rx="2"/>
  
  <!-- Dettagli del manico -->
  <line x1="4" y1="18.5" x2="12" y2="18.5" stroke="#654321" stroke-width="0.3"/>
  <line x1="4" y1="21.5" x2="12" y2="21.5" stroke="#654321" stroke-width="0.3"/>
  
  <!-- Riflesso sulla lama -->
  <line x1="20" y1="19" x2="90" y2="19" stroke="#FFFFFF" stroke-width="0.8" opacity="0.7"/>
  
  <!-- Testo KATANA -->
  <text x="60" y="35" font-family="Arial, sans-serif" font-size="8" font-weight="bold" text-anchor="middle" fill="#2C2C2C">KATANA</text>
</svg>
    '''
    return svg_content

def save_logo_as_png(size=(120, 40)):
    """Salva il logo come PNG usando PIL"""
    # Crea un'immagine con sfondo trasparente
    img = Image.new('RGBA', size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(img)
    
    # Disegna una katana stilizzata
    # Lama
    draw.rectangle([15, 18, 95, 22], fill=(230, 230, 230, 255), outline=(150, 150, 150, 255))
    # Punta
    draw.polygon([(95, 18), (105, 20), (95, 22)], fill=(230, 230, 230, 255), outline=(150, 150, 150, 255))
    # Guardia
    draw.rectangle([12, 16, 18, 24], fill=(44, 44, 44, 255), outline=(0, 0, 0, 255))
    # Manico
    draw.rectangle([2, 17, 14, 23], fill=(139, 69, 19, 255), outline=(101, 67, 33, 255))
    
    return img

if __name__ == "__main__":
    # Salva il logo SVG
    svg_content = create_katana_logo_svg()
    with open('katana_logo.svg', 'w', encoding='utf-8') as f:
        f.write(svg_content)
    
    # Salva il logo PNG
    logo_img = save_logo_as_png()
    logo_img.save('katana_logo.png')
    
    print("Logo Katana creato: katana_logo.svg e katana_logo.png")