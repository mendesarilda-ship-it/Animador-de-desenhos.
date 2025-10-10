import streamlit as st
from PIL import Image
import numpy as np

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
import os
import tempfile
import math

# --- 2. FUNÇÃO PRINCIPAL DE GERAÇÃO DE VÍDEO (AGORA COM RECORTES) ---
def create_cartoon_animation(parts, duration_sec, fps):
    """
    Cria uma animação de recortes (cutout animation) a partir de clipes de partes separadas.
    """
    try:
        clip_duration = duration_sec
        final_clips = []
        
        # ----------------------------------------------------------------------
        # PASSO 1: CARREGAR E PREPARAR AS PARTES ESTÁTICAS (ORDEM DE COMPOSIÇÃO: Fundo -> Frente)
        # ----------------------------------------------------------------------
        
        # O MoviePy compõe os clipes na ordem em que são listados.
        
        # Partes da Base (FUNDÃO)
        base_parts = ['Tronco/Corpo Base', 'Vestido', 'Perna']
        
        # Partes de Cima (FRENTE)
        front_parts = ['Mão Direita', 'Mão Esquerda', 'Dedos', 'Cabelo', 'Olhos']
        
        # ----------------------------------------------------------------------
        # 1. TRONCO (Corpo Base - FUNDO) - Essencial para definir o tamanho do vídeo
        # ----------------------------------------------------------------------
        if 'Tronco/Corpo Base' in parts:
            np_base = np.array(parts['Tronco/Corpo Base'].convert("RGBA"))
            clip_base = ImageClip(np_base, duration=clip_duration).set_pos(("center", "center"))
            
            # Definimos o tamanho final do vídeo baseado no tronco
            video_size = clip_base.size
            final_clips.append(clip_base)
        else:
            # Não pode animar sem o corpo base
            st.error("É necessário carregar o arquivo 'Tronco/Corpo Base' para iniciar a animação.")
            return None
        
        # ----------------------------------------------------------------------
        # 2. OUTRAS PARTES ESTÁTICAS (sem movimento por enquanto)
        # ----------------------------------------------------------------------
        
        # Adiciona Vestido e Perna (geralmente estáticos ou com movimento mínimo)
        for name in ['Vestido', 'Perna']:
            if name in parts:
                np_part = np.array(parts[name].convert("RGBA"))
                clip_part = ImageClip(np_part, duration=clip_duration).set_pos(("center", "center"))
                final_clips.append(clip_part)
                
        # ----------------------------------------------------------------------
        # 3. EXEMPLO BÁSICO DE MOVIMENTO: MÃO ESQUERDA
        # ----------------------------------------------------------------------
        
        if 'Mão Esquerda' in parts:
            np_mao_esq = np.array(parts['Mão Esquerda'].convert("RGBA"))
            clip_mao_esq = ImageClip(np_mao_esq, duration=clip_duration)
            
            # POSICIONAMENTO DA JUNTA (AJUSTE MANUAL CRÍTICO!)
            # Você deve ajustar esses valores (X, Y) para o ponto do ombro na sua imagem de recorte
            OMBRO_X = video_size[0] * 0.55  # Exemplo: 55% da largura
            OMBRO_Y = video_size[1] * 0.40  # Exemplo: 40% da altura (parte superior)
            
            # 1. POSIÇÃO DA PARTE (Onde o ombro vai estar na tela)
            clip_mao_esq = clip_mao_esq.set_pos((OMBRO_X, OMBRO_Y))
            
            # 2. FUNÇÃO DE MOVIMENTO (Rotação: -10 graus a 10 graus)
            def get_rotation(t):
                # Rotação suave (senoidal) para simular um aceno leve
                return 10 * math.sin(2 * math.pi * t / clip_duration) 

            # 3. APLICAR ROTAÇÃO
            # O 'center=(0,0)' é crucial para garantir que a rotação aconteça a partir do centro do clipe.
            clip_mao_esq = clip_mao_esq.fx(lambda clip: clip.rotate(get_rotation, resample='bicubic', center=(0,0)))
            
            final_clips.append(clip_mao_esq)
            
        # ----------------------------------------------------------------------
        # 4. ÚLTIMAS PARTES (ROSTO, CABEÇA) - FRENTE DA COMPOSIÇÃO
        # ----------------------------------------------------------------------

        # Adiciona Cabelo, Olhos, Mão Direita e Dedos (geralmente por cima de tudo)
        for name in ['Cabelo', 'Olhos', 'Mão Direita', 'Dedos']:
            if name in parts:
                np_part = np.array(parts[name].convert("RGBA"))
                clip_part = ImageClip(np_part, duration=clip_duration).set_pos(("center", "center"))
                final_clips.append(clip_part)


        # ----------------------------------------------------------------------
        # 5. COMPOSIÇÃO FINAL
        # ----------------------------------------------------------------------
        
        # Junta todos os clipes de partes do corpo (estáticos e animados)
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
        st.warning("Verifique se você carregou todas as partes necessárias e se o 'packages.txt' com 'ffmpeg' está na raiz.")
        return None

# --- 3. INTERFACE STREAMLIT COM MÚLTIPLOS UPLOADS ---
st.set_page_config(page_title="Gerador de Vídeo de Recortes", layout="wide")
st.title("🎬 Animação de Recortes (Cutout Animation)")

st.sidebar.header("1. Carregar Partes (PNG Transparente)")

# Mapeamento dos uploads para nomes de partes
uploaded_parts = {}

# Lista de partes que o usuário deve carregar (incluindo "dedos")
part_names = [
    'Tronco/Corpo Base',
    'Vestido', 
    'Perna',
    'Cabelo', 
    'Olhos', 
    'Mão Direita', 
    'Mão Esquerda', 
    'Dedos' # Novo!
]

# Cria os botões de upload dinamicamente
for name in part_names:
    file = st.sidebar.file_uploader(f"Carregar: {name} (.png)", key=name, type=["png"])
    if file:
        uploaded_parts[name] = Image.open(file)

st.sidebar.header("2. Configurações")
# Parâmetros
duration = st.sidebar.slider("Duração do Vídeo (segundos)", 
                             min_value=3, max_value=10, value=5)
fps = st.sidebar.slider("Quadros por Segundo (FPS)", 
                        min_value=10, max_value=30, value=24)


if st.button("3. Gerar Animação"):
    
    # ----------------------------------------------------------------------
    # VERIFICAÇÃO MÍNIMA (O corpo base é obrigatório)
    # ----------------------------------------------------------------------
    if 'Tronco/Corpo Base' not in uploaded_parts:
        st.error("Por favor, carregue a imagem do 'Tronco/Corpo Base' para iniciar.")
    else:
        # ----------------------------------------------------------------------
        # PROCESSO DE GERAÇÃO
        # ----------------------------------------------------------------------
        video_output_path = None
        try:
            with st.spinner(f"Compondo animação de {duration}s..."):
                # Passa o dicionário de imagens PIL para a função de animação
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
            # Limpa os arquivos temporários
            if video_output_path and os.path.exists(video_output_path):
                os.unlink(video_output_path)
            
else:
    st.info("Carregue as partes da sua personagem na barra lateral e clique em 'Gerar Animação'.")
