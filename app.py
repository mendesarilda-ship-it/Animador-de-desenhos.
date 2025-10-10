import streamlit as st
from PIL import Image
import numpy as np
import os
import tempfile
import math # <--- GARANTIDO: IMPORTAÇÃO ESSENCIAL PARA ANIMAÇÃO SINUSOIDAL

# --- 1. CORREÇÃO CRÍTICA DE ERRO (PIL/Pillow > 9.0) ---
# Garante a compatibilidade com MoviePy 1.0.3 resolvendo o erro ANTIALIAS
try:
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.Resampling.LANCZOS
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except AttributeError:
    # Fallback para LANCZOS se ANTIALIAS falhar totalmente
    Image.ANTIALIAS = Image.Resampling.LANCZOS


from moviepy.editor import ImageClip, concatenate_videoclips, CompositeVideoClip


# --- 2. FUNÇÃO PRINCIPAL DE GERAÇÃO DE VÍDEO (AGORA COM RECORTES) ---
def create_cartoon_animation(parts, duration_sec, fps):
    """
    Cria uma animação de recortes (cutout animation) a partir de clipes de partes separadas.
    """
    try:
        clip_duration = duration_sec
        final_clips = []
        
        # ----------------------------------------------------------------------
        # PASSO 1: CARREGAR E PREPARAR AS PARTES NA ORDEM DE COMPOSIÇÃO (Fundo -> Frente)
        # ----------------------------------------------------------------------
        
        # O "Vestido e Tronco" é a base, então ele deve ser o primeiro.
        if 'Vestido e Tronco' not in parts:
            # Esta verificação já é feita no bloco 'if st.button'
            return None
        
        np_base_body = np.array(parts['Vestido e Tronco'].convert("RGBA"))
        clip_base_body = ImageClip(np_base_body, duration=clip_duration).set_pos(("center", "center"))
        video_size = clip_base_body.size # Define o tamanho final do vídeo baseado nesta peça
        final_clips.append(clip_base_body)

        
        # --- PERNAS (Perna 1 e Perna 2) ---
        if 'Perna 1' in parts:
            np_perna1 = np.array(parts['Perna 1'].convert("RGBA"))
            clip_perna1 = ImageClip(np_perna1, duration=clip_duration)
            # POSICIONAMENTO DA PERNA 1 (AJUSTE MANUAL!)
            clip_perna1 = clip_perna1.set_pos((video_size[0]*0.45, video_size[1]*0.65)) 
            final_clips.append(clip_perna1)

        if 'Perna 2' in parts:
            np_perna2 = np.array(parts['Perna 2'].convert("RGBA"))
            clip_perna2 = ImageClip(np_perna2, duration=clip_duration)
            # POSICIONAMENTO DA PERNA 2 (AJUSTE MANUAL!)
            clip_perna2 = clip_perna2.set_pos((video_size[0]*0.55, video_size[1]*0.65)) 
            final_clips.append(clip_perna2)


        # --- BRAÇO ESQUERDO (Com Animação) ---
        if 'Braço Esquerdo' in parts:
            np_braco_esq = np.array(parts['Braço Esquerdo'].convert("RGBA"))
            clip_braco_esq = ImageClip(np_braco_esq, duration=clip_duration)
            
            # POSICIONAMENTO DA JUNTA (AJUSTE MANUAL CRÍTICO!)
            OMBRO_ESQ_X = video_size[0] * 0.45 
            OMBRO_ESQ_Y = video_size[1] * 0.35 
            
            clip_braco_esq = clip_braco_esq.set_pos((OMBRO_ESQ_X, OMBRO_ESQ_Y))
            
            # FUNÇÃO DE MOVIMENTO (Aceno Simples)
            def get_rotation_esq(t):
                # Rotação suave (senoidal) de -10 a 10 graus
                return 10 * math.sin(2 * math.pi * t / clip_duration) 

            # APLICAR ROTAÇÃO (Ajuste o 'center' para o ponto do ombro dentro do PNG do braço)
            clip_braco_esq = clip_braco_esq.fx(
                lambda clip: clip.rotate(
                    get_rotation_esq, 
                    resample='bicubic', 
                    center=(clip.w * 0.1, clip.h * 0.1) 
                )
            )
            final_clips.append(clip_braco_esq)


        # --- BRAÇO DIREITO (Estático) ---
        if 'Braço Direito' in parts:
            np_braco_dir = np.array(parts['Braço Direito'].convert("RGBA"))
            clip_braco_dir = ImageClip(np_braco_dir, duration=clip_duration)
            OMBRO_DIR_X = video_size[0] * 0.55 
            OMBRO_DIR_Y = video_size[1] * 0.35 
            clip_braco_dir = clip_braco_dir.set_pos((OMBRO_DIR_X, OMBRO_DIR_Y))
            final_clips.append(clip_braco_dir)
            
        # --- DEDOS ---
        if 'Dedos' in parts:
            np_dedos = np.array(parts['Dedos'].convert("RGBA"))
            clip_dedos = ImageClip(np_dedos, duration=clip_duration)
            # Posição dos Dedos: Offset da Mão Esquerda
            clip_dedos = clip_dedos.set_pos((OMBRO_ESQ_X + 50, OMBRO_ESQ_Y + 100)) # Ajuste
            final_clips.append(clip_dedos)

        # --- CABEÇA ---
        if 'Cabeça' in parts:
            np_cabeca = np.array(parts['Cabeça'].convert("RGBA"))
            clip_cabeca = ImageClip(np_cabeca, duration=clip_duration)
            clip_cabeca = clip_cabeca.set_pos(("center", video_size[1]*0.15)) 
            final_clips.append(clip_cabeca)
            
        # --- OLHOS ---
        if 'Olhos' in parts:
            np_olhos = np.array(parts['Olhos'].convert("RGBA"))
            clip_olhos = ImageClip(np_olhos, duration=clip_duration)
            clip_olhos = clip_olhos.set_pos(("center", video_size[1]*0.25))
            final_clips.append(clip_olhos)


        # ----------------------------------------------------------------------
        # PASSO 2: COMPOSIÇÃO FINAL
        # ----------------------------------------------------------------------
        
        final_clip = CompositeVideoClip(final_clips, size=video_size)
        final_clip = final_clip.set_fps(fps)

        # Salva o arquivo de vídeo temporário
        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as temp_file:
            output_path = temp_file.name
            
        final_clip.write_videofile(
            output_path, 
            codec='libx264', 
            audio_codec='aac',
            temp_audiofile='temp-audio.m4a',
            remove_temp=True,
            verbose=False, 
            logger=None
        )
        
        return output_path

    except Exception as e:
        st.error(f"Erro ao gerar o vídeo: {e}")
        st.warning("Verifique se você carregou todas as partes necessárias, se são PNGs transparentes e se o 'packages.txt' com 'ffmpeg' está na raiz.")
        return None

# --- 3. INTERFACE STREAMLIT COM MÚLTIPLOS UPLOADS ---
st.set_page_config(page_title="Gerador de Vídeo de Recortes", layout="wide")
st.title("🎬 Animação de Recortes (Cutout Animation)")

st.sidebar.header("1. Carregar Partes (PNG Transparente)")

uploaded_parts = {}

# Lista de partes que o usuário deve carregar, baseada nas suas imagens
part_names = [
    'Vestido e Tronco',
    'Cabeça',
    'Olhos',
    'Braço Esquerdo',
    'Braço Direito',
    'Perna 1',
    'Perna 2',
    'Dedos' 
]

# Cria os botões de upload dinamicamente
for name in part_names:
    file = st.sidebar.file_uploader(f"Carregar: {name} (.png)", key=name, type=["png", "jpg", "jpeg"]) # Adicionando JPG/JPEG por segurança
    if file:
        # Tenta abrir como PIL Image, se for JPG/JPEG, converte para RGBA (transparência)
        img = Image.open(file)
        if img.mode != 'RGBA':
            img = img.convert('RGBA')
        uploaded_parts[name] = img

st.sidebar.header("2. Configurações")

duration = st.sidebar.slider("Duração do Vídeo (segundos)", 
                             min_value=3, max_value=10, value=5)
fps = st.sidebar.slider("Quadros por Segundo (FPS)", 
                        min_value=10, max_value=30, value=24)


if st.button("3. Gerar Animação"):
    
    if 'Vestido e Tronco' not in uploaded_parts:
        st.error("Por favor, carregue a imagem do 'Vestido e Tronco' para iniciar.")
    else:
        video_output_path = None
        try:
            with st.spinner(f"Compondo animação de {duration}s..."):
                video_output_path = create_cartoon_animation(uploaded_parts, duration, fps)
            
            if video_output_path:
                st.subheader("Vídeo Gerado!")
                
                with open(video_output_path, "rb") as video_file:
                    video_bytes = video_file.read()
                
                st.video(video_bytes, format='video/mp4')
                
                st.download_button(
                    label="Baixar Vídeo MP4",
                    data=video_bytes,
                    file_name="animacao_recortes.mp4",
                    mime="video/mp4"
                )
                
        finally:
            if video_output_path and os.path.exists(video_output_path):
                os.unlink(video_output_path)
