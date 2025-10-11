import streamlit as st
from PIL import Image
import numpy as np
import os
import tempfile
import math 

# --- 1. CORREÇÃO CRÍTICA DE ERRO (PIL/Pillow > 9.0) ---
try:
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.Resampling.LANCZOS
    if not hasattr(Image, 'ANTIALIAS'):
        Image.ANTIALIAS = Image.LANCZOS
except AttributeError:
    Image.ANTIALIAS = Image.Resampling.LANCZOS


from moviepy.editor import ImageClip, concatenate_videoclips, CompositeVideoClip


# --- 2. FUNÇÃO PRINCIPAL DE GERAÇÃO DE VÍDEO (CUTOUT ANIMATION) ---
def create_cartoon_animation(parts, duration_sec, fps):
    """
    Cria uma animação de recortes (cutout animation) a partir de clipes de partes separadas.
    """
    try:
        clip_duration = duration_sec
        final_clips = []
        
        # ----------------------------------------------------------------------
        # PONTOS DE PIVÔ E MOVIMENTO (Para ajuste fino após o primeiro deploy)
        # ----------------------------------------------------------------------
        
        # Posições de Conexão no Corpo Base
        OMBRO_ESQ_X = 0.45 
        OMBRO_DIR_X = 0.55
        OMBRO_Y = 0.35
        QUADRIL_Y = 0.65
        
        # Frequências e Amplitudes para balanço
        SWAY_FREQ = 1.0 # Balanço principal do corpo (1 ciclo por segundo)
        WALK_FREQ = 2.0 # Frequência de marcha (2 ciclos por segundo)
        BREATH_AMP = 5 # Amplitude de subida/descida (pixels)
        SWAY_ROT_AMP = 0.5 # Amplitude de rotação (graus)

        # ----------------------------------------------------------------------
        # PASSO 3: ADICIONAR MOVIMENTO AO TRONCO E AO CORPO BASE (RESPIRAÇÃO E BALANÇO GERAL)
        # ----------------------------------------------------------------------
        
        if 'Tronco/Vestido' not in parts:
            st.error("É necessário carregar o arquivo 'Tronco/Vestido' para iniciar a animação.")
            return None
        
        np_base_body = np.array(parts['Tronco/Vestido'].convert("RGBA"))
        clip_base_body = ImageClip(np_base_body, duration=clip_duration).set_pos(("center", "center"))
        video_size = clip_base_body.size 
        
        # FUNÇÃO DE MOVIMENTO DO TRONCO
        def get_trunk_position(t):
            # Movimento suave vertical (simula respiração/balanço)
            y_offset = BREATH_AMP * math.sin(2 * math.pi * SWAY_FREQ * t) 
            return ('center', 'center', y_offset)
            
        def get_trunk_rotation(t):
            # Rotação lateral suave
            return SWAY_ROT_AMP * math.sin(2 * math.pi * SWAY_FREQ * t / 2) # Frequência mais lenta

        clip_base_body = clip_base_body.set_position(get_trunk_position)
        clip_base_body = clip_base_body.fx(lambda clip: clip.rotate(get_trunk_rotation, resample='bicubic'))
        final_clips.append(clip_base_body)
        
        # ----------------------------------------------------------------------
        # PASSO 4: PERNAS (MARCHA) - Movimento de balanço frontal/traseiro
        # ----------------------------------------------------------------------
        
        # PERNA 1 (Movimento em fase)
        if 'Perna 1' in parts:
            np_perna1 = np.array(parts['Perna 1'].convert("RGBA"))
            clip_perna1 = ImageClip(np_perna1, duration=clip_duration)
            
            def get_perna1_rotation(t):
                # Balança para frente e para trás
                return 15 * math.sin(2 * math.pi * WALK_FREQ * t)
            
            clip_perna1 = clip_perna1.set_pos((video_size[0]*OMBRO_ESQ_X, video_size[1]*QUADRIL_Y)) # Posição do Quadril
            clip_perna1 = clip_perna1.fx(lambda clip: clip.rotate(get_perna1_rotation, resample='bicubic'))
            final_clips.append(clip_perna1)

        # PERNA 2 (Movimento fora de fase)
        if 'Perna 2' in parts:
            np_perna2 = np.array(parts['Perna 2'].convert("RGBA"))
            clip_perna2 = ImageClip(np_perna2, duration=clip_duration)
            
            def get_perna2_rotation(t):
                # Balança para frente e para trás, mas com fase oposta (+pi)
                return 15 * math.sin(2 * math.pi * WALK_FREQ * t + math.pi) 
            
            clip_perna2 = clip_perna2.set_pos((video_size[0]*OMBRO_DIR_X, video_size[1]*QUADRIL_Y)) # Posição do Quadril
            clip_perna2 = clip_perna2.fx(lambda clip: clip.rotate(get_perna2_rotation, resample='bicubic'))
            final_clips.append(clip_perna2)


        # ----------------------------------------------------------------------
        # PASSO 5: BRAÇOS (ACENO/BALANÇO)
        # ----------------------------------------------------------------------

        # BRAÇO ESQUERDO (Movimento de Aceno - Forte)
        if 'Braço Esquerdo' in parts:
            np_braco_esq = np.array(parts['Braço Esquerdo'].convert("RGBA"))
            clip_braco_esq = ImageClip(np_braco_esq, duration=clip_duration)
            
            def get_rotation_esq(t):
                # Aceno mais pronunciado
                return 20 * math.sin(2 * math.pi * t / clip_duration) 
            
            clip_braco_esq = clip_braco_esq.set_pos((video_size[0]*OMBRO_ESQ_X, video_size[1]*OMBRO_Y))
            clip_braco_esq = clip_braco_esq.fx(lambda clip: clip.rotate(get_rotation_esq, resample='bicubic'))
            final_clips.append(clip_braco_esq)


        # BRAÇO DIREITO (Balanço Suave - Fora de Fase com o esquerdo)
        if 'Braço Direito' in parts:
            np_braco_dir = np.array(parts['Braço Direito'].convert("RGBA"))
            clip_braco_dir = ImageClip(np_braco_dir, duration=clip_duration)
            
            def get_rotation_dir(t):
                # Balanço suave, fora de fase do braço esquerdo para evitar robotização
                return 10 * math.sin(2 * math.pi * t / clip_duration + math.pi / 2) 
                
            clip_braco_dir = clip_braco_dir.set_pos((video_size[0]*OMBRO_DIR_X, video_size[1]*OMBRO_Y))
            clip_braco_dir = clip_braco_dir.fx(lambda clip: clip.rotate(get_rotation_dir, resample='bicubic'))
            final_clips.append(clip_braco_dir)
            
        # ----------------------------------------------------------------------
        # PASSO 6: CABEÇA, CABELO E OLHOS (Animação de "Vida")
        # ----------------------------------------------------------------------

        # FUNÇÕES GLOBAIS PARA CABEÇA E OLHOS
        def get_head_pos(t):
            # Balanço horizontal suave da cabeça (para simular inércia)
            x_offset = 3 * math.sin(2 * math.pi * SWAY_FREQ * t / 2) 
            y_offset = BREATH_AMP * math.sin(2 * math.pi * SWAY_FREQ * t) * 0.5 # metade da respiração do tronco
            return ('center', video_size[1]*0.15 + y_offset, x_offset)

        def get_head_rotation(t):
            # Rotação suave da cabeça (para compensar o tronco)
            return 1.0 * math.sin(2 * math.pi * SWAY_FREQ * t / 2) 
            
        
        # CABEÇA
        if 'Cabeça' in parts:
            np_cabeca = np.array(parts['Cabeça'].convert("RGBA"))
            clip_cabeca = ImageClip(np_cabeca, duration=clip_duration)
            
            clip_cabeca = clip_cabeca.set_position(get_head_pos)
            clip_cabeca = clip_cabeca.fx(lambda clip: clip.rotate(get_head_rotation, resample='bicubic'))
            final_clips.append(clip_cabeca)
            
        # CABELO (Segue o movimento da cabeça, mas com um pouco mais de balanço/inércia)
        if 'Cabelo' in parts:
            np_cabelo = np.array(parts['Cabelo'].convert("RGBA"))
            clip_cabelo = ImageClip(np_cabelo, duration=clip_duration)
            
            clip_cabelo = clip_cabelo.set_position(get_head_pos)
            # Rotação ligeiramente mais exagerada para dar sensação de movimento pendular
            clip_cabelo = clip_cabelo.fx(lambda clip: clip.rotate(get_head_rotation(t) * 1.5, resample='bicubic'))
            final_clips.append(clip_cabelo)

        # OLHOS (Apenas seguem a posição da cabeça, sem rotação própria)
        if 'Olhos' in parts:
            np_olhos = np.array(parts['Olhos'].convert("RGBA"))
            clip_olhos = ImageClip(np_olhos, duration=clip_duration)
            # Os olhos seguem o centro X, mas a altura é corrigida para o centro da face
            clip_olhos = clip_olhos.set_position(get_head_pos)
            final_clips.append(clip_olhos)


        # ----------------------------------------------------------------------
        # PASSO 7: COMPOSIÇÃO FINAL
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

part_names = [
    'Tronco/Vestido',
    'Cabeça',
    'Cabelo',
    'Olhos',
    'Braço Esquerdo',
    'Braço Direito',
    'Perna 1', 
    'Perna 2'
]

for name in part_names:
    file = st.sidebar.file_uploader(f"Carregar: {name} (.png)", key=name, type=["png", "jpg", "jpeg"]) 
    if file:
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
    
    if 'Tronco/Vestido' not in uploaded_parts:
        st.error("Por favor, carregue a imagem do 'Tronco/Vestido' para iniciar.")
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
